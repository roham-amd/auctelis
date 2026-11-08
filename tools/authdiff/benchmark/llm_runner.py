"""Model-agnostic AgentSecBench LLM scoring.

Does not invoke models. Scores submitted agent finding JSON against expert
ground truth. Deterministic Guard benchmarks remain in ``runner.py`` /
``authdiff benchmark run`` and ``authdiff benchmark rules``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from authdiff.benchmark.governance import (
    dataset_manifest_path,
    evaluation_pin,
    filter_cases_by_split,
    llm_cases_root,
    verify_dataset_integrity,
)
from authdiff.versioning import load_versions


def _load_llm_cases() -> list[dict[str, Any]]:
    cases_dir = llm_cases_root() / "cases"
    if not cases_dir.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(cases_dir.glob("LLM-*.json"))]


def _load_dataset_manifest() -> dict[str, Any]:
    path = dataset_manifest_path()
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        return {}
    return doc


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _title_overlap(a: str, b: str) -> bool:
    ta = set(_norm(a).split())
    tb = set(_norm(b).split())
    if not ta or not tb:
        return False
    return len(ta & tb) / max(1, len(ta | tb)) >= 0.35


def _severity_close(predicted: str, expected: str) -> bool:
    order = ["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    try:
        return abs(order.index(predicted) - order.index(expected)) <= 1
    except ValueError:
        return predicted == expected


def _score_submission(case: dict[str, Any], submission: dict[str, Any]) -> dict[str, Any]:
    """Score one agent submission against ground truth findings."""
    gt = list(case.get("ground_truth_findings") or [])
    predicted = list(submission.get("findings") or [])
    matched_gt: set[str] = set()
    matched_pred: set[int] = set()
    evidence_ok = 0
    evidence_checked = 0
    severity_ok = 0
    severity_checked = 0
    hallucinated = 0

    for i, pred in enumerate(predicted):
        title = str(pred.get("title") or "")
        status = str(pred.get("status") or pred.get("confidence") or "")
        evidence_ids = list(pred.get("evidence_ids") or [])
        hit = None
        for g in gt:
            gid = str(g.get("finding_id") or "")
            if gid in matched_gt:
                continue
            if _title_overlap(title, str(g.get("title") or "")):
                hit = g
                matched_gt.add(gid)
                matched_pred.add(i)
                break
        if hit is None:
            if status in {"CONFIRMED"} or str(pred.get("severity") or "") in {
                "HIGH",
                "CRITICAL",
            }:
                hallucinated += 1
            # Also count unmatched predictions as false positives via fp below.
            continue

        evidence_checked += 1
        if evidence_ids:
            evidence_ok += 1
        if status == "CONFIRMED" and not evidence_ids:
            # Confirmed without evidence is both evidence failure and unsupported.
            hallucinated += 1

        severity_checked += 1
        if _severity_close(str(pred.get("severity") or ""), str(hit.get("severity") or "")):
            severity_ok += 1

        must_not = [str(x).lower() for x in (hit.get("must_not_claim") or [])]
        for banned in must_not:
            if "confirmed runtime" in banned and "confirmed" in status.lower():
                classes = str(pred.get("evidence_classes") or []).lower()
                if "runtime" not in classes:
                    hallucinated += 1

    tp = len(matched_gt)
    fp = max(0, len(predicted) - len(matched_pred))
    fn = max(0, len(gt) - len(matched_gt))
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 1.0
    evidence_acc = evidence_ok / evidence_checked if evidence_checked else 1.0
    severity_cal = severity_ok / severity_checked if severity_checked else 1.0

    return {
        # Flat fields retained for floors / simple consumers.
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "evidence_accuracy": round(evidence_acc, 4),
        "severity_calibration": round(severity_cal, 4),
        "hallucinated_claims": hallucinated,
        "ground_truth_count": len(gt),
        "predicted_count": len(predicted),
        # Separated quality dimensions (preferred reporting shape).
        "detection_quality": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        },
        "evidence_quality": {
            "evidence_accuracy": round(evidence_acc, 4),
            "matched_with_evidence": evidence_ok,
            "matched_checked": evidence_checked,
        },
        "severity_quality": {
            "severity_calibration": round(severity_cal, 4),
            "matched_checked": severity_checked,
        },
        "unsupported_claims": {
            "hallucinated_claims": hallucinated,
        },
    }


def _validate_cases(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    results: list[dict[str, Any]] = []
    failed = 0
    for case in cases:
        errors: list[str] = []
        if not case.get("id"):
            errors.append("missing id")
        if "ground_truth_findings" not in case or not isinstance(
            case.get("ground_truth_findings"), list
        ):
            errors.append("ground_truth_findings must be a list (empty allowed for negatives)")
        if not case.get("review"):
            errors.append("missing review metadata (reviewer / reviewed_at / status)")
        for g in case.get("ground_truth_findings") or []:
            if not g.get("finding_id") or not g.get("title"):
                errors.append("ground truth entries need finding_id and title")
            if g.get("status") == "CONFIRMED" and not g.get("required_evidence"):
                errors.append(f"{g.get('finding_id')}: CONFIRMED needs required_evidence")
        ok = not errors
        if not ok:
            failed += 1
        results.append({"id": case.get("id"), "ok": ok, "errors": errors, "mode": "validate"})
    return results, failed


def _submission_sets(root: Path) -> list[tuple[str, Path]]:
    """Return (agent_label, directory) pairs.

    A flat directory of ``*.json`` is one agent set. Nested directories each
    containing JSON are treated as separate pilot agents.
    """
    direct = list(root.glob("*.json"))
    subdirs = [p for p in sorted(root.iterdir()) if p.is_dir() and list(p.glob("*.json"))]
    if subdirs and not direct:
        return [(p.name, p) for p in subdirs]
    return [(root.name, root)]


def _score_agent_dir(
    agent: str,
    directory: Path,
    by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    results: list[dict[str, Any]] = []
    failed = 0
    for path in sorted(directory.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        case_id = str(doc.get("case_id") or path.stem)
        case = by_id.get(case_id)
        if case is None:
            failed += 1
            results.append(
                {
                    "id": case_id,
                    "agent": agent,
                    "ok": False,
                    "errors": [f"no LLM case for {case_id}"],
                    "submission": str(path),
                }
            )
            continue
        scores = _score_submission(case, doc)
        floors = case.get("score_floors") or {}
        errors: list[str] = []
        if scores["precision"] < float(floors.get("precision", 0.0)):
            errors.append(f"precision {scores['precision']} below floor")
        if scores["recall"] < float(floors.get("recall", 0.0)):
            errors.append(f"recall {scores['recall']} below floor")
        if scores["hallucinated_claims"] > int(floors.get("max_hallucinations", 10**9)):
            errors.append("too many hallucinated claims")
        if scores["evidence_accuracy"] < float(floors.get("evidence_accuracy", 0.0)):
            errors.append(f"evidence_accuracy {scores['evidence_accuracy']} below floor")
        if scores["severity_calibration"] < float(floors.get("severity_calibration", 0.0)):
            errors.append(f"severity_calibration {scores['severity_calibration']} below floor")
        ok = not errors
        if not ok:
            failed += 1
        results.append(
            {
                "id": case_id,
                "agent": agent,
                "ok": ok,
                "errors": errors,
                "scores": scores,
                "model": doc.get("model"),
                "submission": str(path),
            }
        )
    return results, failed


def run_llm_benchmark(
    *,
    submissions: Path | None = None,
    validate_only: bool = False,
    split: str = "all",
) -> dict[str, Any]:
    all_cases = _load_llm_cases()
    manifest = _load_dataset_manifest()
    integrity = verify_dataset_integrity(manifest)
    cases = filter_cases_by_split(all_cases, split=split, manifest=manifest)  # type: ignore[arg-type]
    bench_ver = load_versions().get("agent_benchmark_llm", "0.1.0")
    dataset_ver = str(manifest.get("dataset_version") or bench_ver)
    rubric_ver = str(manifest.get("rubric_version") or "1.0.0")

    common_meta = {
        "benchmark_version": bench_ver,
        "benchmark_name": "AgentSecBench-LLM",
        "dataset_version": dataset_ver,
        "rubric_version": rubric_ver,
        "split": split,
        "case_count": len(cases),
        "case_count_all": len(all_cases),
        "dataset_integrity": integrity,
        "deterministic_benchmark_separate": True,
        "evaluation_pin": evaluation_pin(
            split=split, submissions=str(submissions) if submissions else None
        ),
    }

    if validate_only or submissions is None:
        results, failed = _validate_cases(cases if split != "all" else all_cases)
        if not integrity["ok"]:
            failed += 1
            results.append(
                {
                    "id": "DATASET-INTEGRITY",
                    "ok": False,
                    "errors": [
                        f"missing={integrity['missing']}",
                        f"unexpected={integrity['unexpected']}",
                        f"mismatched={integrity['mismatched']}",
                    ],
                    "mode": "integrity",
                }
            )
        return {
            **common_meta,
            "mode": "validate_ground_truth_only",
            "total": len(results),
            "failed": failed,
            "passed": len(results) - failed,
            "results": results,
            "limitations": [
                "No model was invoked.",
                "Offline scoring ≠ live model evaluation — provide --submissions for quality scores.",
                "Do not cite validate-only passes as AI detection quality.",
                "Deterministic `authdiff benchmark run|rules` remain a separate suite.",
                "Held-out cases must not be used to tune the scorer or prompts.",
            ],
        }

    if not submissions.is_dir():
        return {
            **common_meta,
            "mode": "score_submissions",
            "total": 0,
            "failed": 1,
            "passed": 0,
            "results": [],
            "errors": [f"submissions directory not found: {submissions}"],
        }

    if not integrity["ok"]:
        return {
            **common_meta,
            "mode": "score_submissions",
            "total": 0,
            "failed": 1,
            "passed": 0,
            "results": [],
            "errors": ["dataset integrity check failed; refusing to score"],
        }

    by_id = {str(c.get("id")): c for c in cases}
    score_results: list[dict[str, Any]] = []
    failed = 0
    agents_scored: list[str] = []
    known_ids = {str(c.get("id")) for c in all_cases}
    for agent, directory in _submission_sets(submissions):
        agents_scored.append(agent)
        agent_results, _agent_failed = _score_agent_dir(agent, directory, by_id)
        # Keep unknown case_id errors; filter known-but-out-of-split silently.
        kept: list[dict[str, Any]] = []
        for row in agent_results:
            cid = str(row.get("id"))
            if cid in known_ids and cid not in by_id:
                continue
            kept.append(row)
        score_results.extend(kept)
        failed += sum(1 for row in kept if not row.get("ok"))

    return {
        **common_meta,
        "mode": "score_submissions",
        "agents_scored": agents_scored,
        "total": len(score_results),
        "failed": failed,
        "passed": len(score_results) - failed,
        "results": score_results,
        "limitations": [
            "Scoring is lexical/structural against expert ground truth — not a substitute for human review.",
            "Model providers are never called by this runner (offline submissions only).",
            "Detection, evidence, and severity qualities are scored separately.",
            "Keep deterministic `authdiff benchmark run|rules` separate from these scores.",
            "Do not publish a definitive leaderboard from maintainer pilots alone.",
        ],
    }
