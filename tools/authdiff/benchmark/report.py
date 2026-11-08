"""Transparent AgentSecBench evaluation reports (offline, no model calls)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from authdiff.benchmark.governance import (
    evaluation_pin,
    filter_cases_by_split,
    verify_dataset_integrity,
)
from authdiff.benchmark.llm_runner import (
    _load_dataset_manifest,
    _load_llm_cases,
    run_llm_benchmark,
)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_evaluation_report(
    *,
    submissions: Path,
    split: str = "all",
    provenance: str = "any",
) -> dict[str, Any]:
    manifest = _load_dataset_manifest()
    integrity = verify_dataset_integrity(manifest)
    cases = filter_cases_by_split(_load_llm_cases(), split=split, manifest=manifest)  # type: ignore[arg-type]
    allowed_ids = {str(c.get("id")) for c in cases}

    # Empty / missing submission dirs yield an honest empty report rather than a crash.
    has_json = False
    if submissions.is_dir():
        has_json = bool(list(submissions.glob("*.json"))) or any(
            p.is_dir() and list(p.glob("*.json")) for p in submissions.iterdir()
        )
    if not has_json:
        return {
            "report_version": "1.1",
            "kind": "agentsecbench_evaluation_report",
            "provenance_filter": provenance,
            "is_external_evidence_report": provenance == "external",
            "evaluation_pin": evaluation_pin(split=split, submissions=str(submissions)),
            "dataset_integrity": integrity,
            "sample_size": {
                "cases_in_split": len(cases),
                "submission_rows": 0,
                "agents": [],
                "valid_external_agents": 0 if provenance == "external" else None,
            },
            "per_agent": {},
            "per_case": {},
            "overall": {
                "detection_quality": {"precision_mean": None, "recall_mean": None},
                "evidence_quality": {"evidence_accuracy_mean": None},
                "severity_quality": {"severity_calibration_mean": None},
                "unsupported_claims": {
                    "hallucinated_claims_total": 0,
                    "hallucinated_claims_mean": None,
                },
                "cases_scored": 0,
                "cases_passing_floors": 0,
            },
            "limitations": [
                "No scored submissions in this report scope.",
                "Templates, samples, and maintainer pilots are not external evidence.",
                "Offline submission scoring is not live model evaluation.",
                "Do not publish a leaderboard from empty or maintainer-only sets.",
                *(manifest.get("limitations") or []),
            ],
            "leaderboard_policy": manifest.get("leaderboard_policy"),
            "ranking_allowed": False,
        }

    raw = run_llm_benchmark(submissions=submissions, split=split)
    # Filter results to the requested split.
    results = [r for r in raw.get("results") or [] if r.get("id") in allowed_ids or not allowed_ids]

    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        by_agent[str(row.get("agent") or "unknown")].append(row)
        by_case[str(row.get("id") or "unknown")].append(row)

    def dim_means(rows: list[dict[str, Any]]) -> dict[str, Any]:
        det_p = [
            float((r.get("scores") or {}).get("precision") or 0) for r in rows if r.get("scores")
        ]
        det_r = [float((r.get("scores") or {}).get("recall") or 0) for r in rows if r.get("scores")]
        evid = [
            float((r.get("scores") or {}).get("evidence_accuracy") or 0)
            for r in rows
            if r.get("scores")
        ]
        sev = [
            float((r.get("scores") or {}).get("severity_calibration") or 0)
            for r in rows
            if r.get("scores")
        ]
        hall = [
            int((r.get("scores") or {}).get("hallucinated_claims") or 0)
            for r in rows
            if r.get("scores")
        ]
        return {
            "detection_quality": {"precision_mean": _mean(det_p), "recall_mean": _mean(det_r)},
            "evidence_quality": {"evidence_accuracy_mean": _mean(evid)},
            "severity_quality": {"severity_calibration_mean": _mean(sev)},
            "unsupported_claims": {
                "hallucinated_claims_total": sum(hall),
                "hallucinated_claims_mean": _mean([float(x) for x in hall]),
            },
            "cases_scored": len(rows),
            "cases_passing_floors": sum(1 for r in rows if r.get("ok")),
        }

    per_agent = {
        agent: {
            "per_case": [
                {
                    "case_id": r.get("id"),
                    "ok": r.get("ok"),
                    "errors": r.get("errors"),
                    "detection_quality": (r.get("scores") or {}).get("detection_quality"),
                    "evidence_quality": (r.get("scores") or {}).get("evidence_quality"),
                    "severity_quality": (r.get("scores") or {}).get("severity_quality"),
                    "unsupported_claims": (r.get("scores") or {}).get("unsupported_claims"),
                    "model": r.get("model"),
                }
                for r in rows
            ],
            "aggregates": dim_means(rows),
        }
        for agent, rows in sorted(by_agent.items())
    }

    per_case = {
        case_id: {
            "split": next(
                (
                    s
                    for s, ids in (manifest.get("splits") or {}).items()
                    if isinstance(ids, list) and case_id in ids
                ),
                "unassigned",
            ),
            "agent_results": [
                {
                    "agent": r.get("agent"),
                    "ok": r.get("ok"),
                    "scores": r.get("scores"),
                    "model": r.get("model"),
                }
                for r in rows
            ],
        }
        for case_id, rows in sorted(by_case.items())
    }

    external_note = (
        "This report is labeled provenance=external. Only independently developed "
        "agent audits with vault intake ok=true count as external evidence."
        if provenance == "external"
        else "Provenance filter is not external; do not cite as external evaluation evidence."
    )
    return {
        "report_version": "1.1",
        "kind": "agentsecbench_evaluation_report",
        "provenance_filter": provenance,
        "is_external_evidence_report": provenance == "external",
        "evaluation_pin": evaluation_pin(split=split, submissions=str(submissions)),
        "dataset_integrity": integrity,
        "sample_size": {
            "cases_in_split": len(cases),
            "submission_rows": len(results),
            "agents": sorted(by_agent.keys()),
            "valid_external_agents": (len(by_agent) if provenance == "external" else None),
        },
        "per_agent": per_agent,
        "per_case": per_case,
        "overall": dim_means(results),
        "limitations": [
            external_note,
            "Sample size is small; do not treat this as a definitive leaderboard.",
            "Offline submission scoring is not live model evaluation.",
            "Maintainer pilot agents are not external credibility evidence.",
            "Templates and sample fixtures are not external evidence.",
            "Held-out scores should not be used to tune prompts or the scorer.",
            *(manifest.get("limitations") or []),
        ],
        "leaderboard_policy": manifest.get("leaderboard_policy"),
        "ranking_allowed": False,
    }
