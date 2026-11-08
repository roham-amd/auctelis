"""External submission intake vault: validate, checksum, preserve, classify provenance.

Treat every external intake as untrusted data: schema/size checks only.
Never execute submitted files, embedded code, or referenced paths.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from authdiff.benchmark.governance import (
    dataset_manifest_path,
    llm_cases_root,
    sha256_file,
    verify_dataset_integrity,
)
from authdiff.jsonio import read_json, write_json
from authdiff.paths import repo_root
from authdiff.versioning import package_version, product_version

REQUIRED_EXECUTION_FIELDS = ("produced_at_utc", "fixture_ref")
ALLOWED_PROVENANCE = {"external", "pilot", "sample", "template"}

# Untrusted-intake limits (bytes / counts). Reject rather than truncate.
MAX_SUBMISSION_FILE_BYTES = 256_000
MAX_SUBMISSION_FILES = 32
MAX_FINDINGS_PER_FILE = 200
MAX_JSON_CHARS = MAX_SUBMISSION_FILE_BYTES


def contract_path() -> Path:
    return llm_cases_root() / "EVALUATION-CONTRACT-0.3.0.json"


def external_root() -> Path:
    return llm_cases_root() / "submissions" / "external"


def vault_root() -> Path:
    return external_root() / "vault"


def collection_root() -> Path:
    return llm_cases_root() / "collection"


def load_contract() -> dict[str, Any]:
    doc = read_json(contract_path())
    if not isinstance(doc, dict):
        raise TypeError(f"evaluation contract must be a JSON object: {contract_path()}")
    return doc


def verify_evaluation_contract() -> dict[str, Any]:
    contract = load_contract()
    manifest = read_json(dataset_manifest_path())
    integrity = verify_dataset_integrity(manifest)
    pins = contract.get("pins") or {}
    errors: list[str] = []
    if pins.get("dataset_version") != manifest.get("dataset_version"):
        errors.append("contract dataset_version != DATASET.json")
    if pins.get("rubric_version") != manifest.get("rubric_version"):
        errors.append("contract rubric_version != DATASET.json")
    if not integrity["ok"]:
        errors.append("dataset integrity failed")
    if not contract.get("frozen"):
        errors.append("contract is not frozen")
    return {
        "ok": not errors and integrity["ok"],
        "contract_id": contract.get("contract_id"),
        "contract_version": contract.get("contract_version"),
        "pins": pins,
        "dataset_integrity": integrity,
        "errors": errors,
        "product_version": product_version(),
        "package_version": package_version(),
    }


def _safe_submission_path(path: Path, source: Path) -> list[str]:
    """Reject symlinks and paths that escape the source directory."""
    errors: list[str] = []
    if path.is_symlink():
        errors.append(f"{path.name}: symlinks are rejected (untrusted intake)")
        return errors
    try:
        path.resolve().relative_to(source.resolve())
    except ValueError:
        errors.append(f"{path.name}: path escapes source directory")
    if path.name != path.name.encode("ascii", "ignore").decode("ascii"):
        errors.append(f"{path.name}: non-ascii filename rejected")
    if not path.name.startswith("LLM-") or not path.name.endswith(".json"):
        errors.append(f"{path.name}: filename must match LLM-*.json")
    return errors


def _read_untrusted_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse JSON as data only — never execute. Enforce size limits first."""
    errors: list[str] = []
    size = path.stat().st_size
    if size > MAX_SUBMISSION_FILE_BYTES:
        return None, [f"file exceeds {MAX_SUBMISSION_FILE_BYTES} bytes ({size})"]
    if size == 0:
        return None, ["empty file"]
    raw = path.read_bytes()
    if b"\x00" in raw:
        return None, ["nul bytes not allowed in submission JSON"]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, ["file is not valid UTF-8"]
    if len(text) > MAX_JSON_CHARS:
        return None, [f"decoded text exceeds {MAX_JSON_CHARS} characters"]
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc.msg}"]
    if not isinstance(doc, dict):
        return None, ["JSON root must be an object"]
    return doc, errors


def _validate_submission_doc(doc: dict[str, Any], *, known_cases: set[str]) -> list[str]:
    errors: list[str] = []
    case_id = str(doc.get("case_id") or "")
    if not case_id:
        errors.append("missing case_id")
    elif case_id not in known_cases:
        errors.append(f"unknown case_id {case_id}")
    if not doc.get("model"):
        errors.append("missing model")
    if "findings" not in doc or not isinstance(doc.get("findings"), list):
        errors.append("findings must be a list")
    elif len(doc["findings"]) > MAX_FINDINGS_PER_FILE:
        errors.append(f"findings exceed limit of {MAX_FINDINGS_PER_FILE}")
    execution = doc.get("execution")
    if not isinstance(execution, dict):
        errors.append("missing execution object")
    else:
        for field in REQUIRED_EXECUTION_FIELDS:
            if not execution.get(field):
                errors.append(f"execution.{field} required")
        claimed = execution.get("dataset_version_claimed")
        if claimed and claimed != "0.3.0":
            errors.append(f"dataset_version_claimed {claimed!r} != 0.3.0")
        if not claimed:
            errors.append("execution.dataset_version_claimed required (must be 0.3.0)")
    return errors


def intake_submission_dir(
    source: Path,
    *,
    agent_id: str,
    provenance: str = "external",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Validate and preserve a submission directory into the immutable vault.

    Security posture: untrusted input. Validate + copy bytes only. Never exec.
    """
    if provenance not in ALLOWED_PROVENANCE:
        return {"ok": False, "errors": [f"provenance must be one of {sorted(ALLOWED_PROVENANCE)}"]}
    if not source.is_dir():
        return {"ok": False, "errors": [f"source not a directory: {source}"]}
    if source.is_symlink():
        return {"ok": False, "errors": ["source directory must not be a symlink"]}

    contract = load_contract()
    manifest = read_json(dataset_manifest_path())
    known = set(manifest.get("splits", {}).get("public") or []) | set(
        manifest.get("splits", {}).get("held_out") or []
    )
    files = sorted(p for p in source.glob("LLM-*.json") if p.is_file() or p.is_symlink())
    if not files:
        return {"ok": False, "errors": ["no LLM-*.json files found"]}
    if len(files) > MAX_SUBMISSION_FILES:
        return {
            "ok": False,
            "errors": [f"too many submission files ({len(files)} > {MAX_SUBMISSION_FILES})"],
        }

    file_results: list[dict[str, Any]] = []
    all_ok = True
    for path in files:
        path_errors = _safe_submission_path(path, source)
        doc: dict[str, Any] | None = None
        errors = list(path_errors)
        digest = ""
        size = path.stat().st_size if path.exists() and not path.is_symlink() else 0
        if not path_errors:
            doc, read_errors = _read_untrusted_json(path)
            errors.extend(read_errors)
            if doc is not None:
                errors.extend(_validate_submission_doc(doc, known_cases=known))
                digest = sha256_file(path)
                size = path.stat().st_size
        ok = not errors
        all_ok = all_ok and ok
        file_results.append(
            {
                "file": path.name,
                "case_id": (doc or {}).get("case_id") or path.stem,
                "ok": ok,
                "errors": errors,
                "sha256": digest,
                "bytes": size,
            }
        )

    received_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Sanitize agent_id for run_id path segment.
    safe_agent = "".join(c if c.isalnum() or c in "-_" else "-" for c in agent_id)[:64] or "agent"
    run_id = f"{safe_agent}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    record = {
        "intake_version": "1.1",
        "run_id": run_id,
        "agent_id": agent_id,
        "provenance": provenance,
        "received_at_utc": received_at,
        "source_path": str(source.resolve()),
        "contract_id": contract.get("contract_id"),
        "dataset_version": "0.3.0",
        "files": file_results,
        "ok": all_ok,
        "is_external_evidence": provenance == "external" and all_ok,
        "trust": {
            "untrusted_input": True,
            "executed_submission": False,
            "max_file_bytes": MAX_SUBMISSION_FILE_BYTES,
            "max_files": MAX_SUBMISSION_FILES,
            "max_findings_per_file": MAX_FINDINGS_PER_FILE,
        },
        "notes": [
            "Original bytes preserved under vault/received/<run_id>/.",
            "Do not mutate files after intake; re-intake creates a new run_id.",
            "Intake never executes submission content.",
        ],
    }

    if dry_run:
        record["dry_run"] = True
        return record

    if not all_ok:
        # Do not write invalid payloads into the immutable evidence vault.
        registry_path = vault_root() / "REGISTRY.jsonl"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with registry_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**record, "vault_written": False}, ensure_ascii=False) + "\n")
        return {**record, "vault_written": False}

    dest = vault_root() / "received" / run_id
    dest.mkdir(parents=True, exist_ok=False)
    for path in files:
        # Copy file contents only (follow_symlinks=False rejects symlink sources earlier).
        shutil.copyfile(path, dest / path.name, follow_symlinks=False)
    write_json(dest / "INTAKE.json", record)

    registry_path = vault_root() / "REGISTRY.jsonl"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({**record, "vault_written": True}, ensure_ascii=False) + "\n")

    return {**record, "vault_written": True}


def list_external_intakes() -> dict[str, Any]:
    """List vault intakes that count as external evidence."""
    registry = vault_root() / "REGISTRY.jsonl"
    rows: list[dict[str, Any]] = []
    if registry.is_file():
        for line in registry.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    external = [
        r
        for r in rows
        if r.get("provenance") == "external" and r.get("ok") and r.get("vault_written", True)
    ]
    return {
        "total_registry_entries": len(rows),
        "valid_external_intakes": len(external),
        "external_run_ids": [r.get("run_id") for r in external],
        "entries": rows,
        "note": "Only provenance=external, ok=true, and vault_written count as external evidence.",
    }


def _invitation_rows() -> list[dict[str, Any]]:
    path = collection_root() / "INVITATIONS.jsonl"
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def collection_status() -> dict[str, Any]:
    """Honest funnel: invitations ≠ responses ≠ submissions ≠ valid intakes."""
    invites = _invitation_rows()
    # Latest status per invitation_id (append-only transitions).
    latest: dict[str, dict[str, Any]] = {}
    for row in invites:
        iid = str(row.get("invitation_id") or "")
        if iid:
            latest[iid] = row
    statuses = [str(r.get("status") or "") for r in latest.values()]
    invitations = len(latest)
    responses = sum(
        1
        for s in statuses
        if s in {"responded", "declined", "package_issued", "submitted", "withdrawn"}
    )
    packages_issued = sum(1 for s in statuses if s in {"package_issued", "submitted"})
    submissions_received = sum(1 for s in statuses if s == "submitted")

    intakes = list_external_intakes()
    valid = int(intakes["valid_external_intakes"])
    agent_ids = {
        str(r.get("agent_id"))
        for r in intakes.get("entries") or []
        if r.get("provenance") == "external" and r.get("ok") and r.get("vault_written", True)
    }

    criteria_path = llm_cases_root() / "COLLECTION-CRITERIA.md"
    status_path = collection_root() / "COLLECTION-STATUS.json"
    declared = read_json(status_path) if status_path.is_file() else {}

    minimum_met = valid >= 3 and len(agent_ids) >= 3
    funnel = {
        "invitations": invitations,
        "responses": responses,
        "packages_issued": packages_issued,
        "submissions_received": submissions_received,
        "valid_external_intakes": valid,
        "distinct_agent_configurations": len(agent_ids),
        "held_out_cases_scored_external": int(
            (declared.get("funnel") or {}).get("held_out_cases_scored_external") or 0
        ),
    }
    return {
        "ok": True,
        "contract_id": "AgentSecBench-LLM-EVAL-0.3.0",
        "dataset_version": "0.3.0",
        "collection_status": declared.get("collection_status") or "open",
        "opened_utc": declared.get("opened_utc"),
        "target_close_utc": declared.get("target_close_utc"),
        "hard_stop_utc": declared.get("hard_stop_utc"),
        "funnel": funnel,
        "minimum_evidence_met": minimum_met,
        "external_run_ids": intakes.get("external_run_ids"),
        "criteria_doc": str(criteria_path.relative_to(repo_root()))
        if criteria_path.is_file()
        else None,
        "notes": [
            "An invitation is not a submission; a submission is not a valid intake.",
            "Zeros are correct until independent valid intakes exist.",
            "Pilots/templates/samples are never counted here as external evidence.",
        ],
        "product_version": product_version(),
        "package_version": package_version(),
    }


def build_submitter_package(output_dir: Path) -> dict[str, Any]:
    """Write task cards without ground-truth findings for submitters."""
    manifest = read_json(dataset_manifest_path())
    cases_dir = llm_cases_root() / "cases"
    output_dir.mkdir(parents=True, exist_ok=True)
    cards: list[dict[str, Any]] = []
    for path in sorted(cases_dir.glob("LLM-*.json")):
        case = read_json(path)
        case_id = str(case.get("id"))
        split = (
            "held_out"
            if case_id in set(manifest.get("splits", {}).get("held_out") or [])
            else "public"
        )
        card = {
            "case_id": case_id,
            "title": case.get("title"),
            "family": case.get("family"),
            "variant": case.get("variant"),
            "split": split,
            "fixture": case.get("fixture"),
            "instructions": [
                "Audit the fixture repository offline.",
                "Emit findings JSON conforming to agentsecbench-submission.schema.json.",
                "Do not request or expect ground-truth answers.",
                "Set execution.dataset_version_claimed to 0.3.0.",
                "Provide agent/model versions, tools_available, and permissions when known.",
            ],
            # Explicitly omit ground_truth_findings
        }
        cards.append(card)
        write_json(output_dir / f"{case_id}.task.json", card)

    write_json(
        output_dir / "PACKAGE.json",
        {
            "package_kind": "agentsecbench_submitter_package",
            "dataset_version": "0.3.0",
            "contract_id": "AgentSecBench-LLM-EVAL-0.3.0",
            "includes_ground_truth": False,
            "case_count": len(cards),
            "held_out_case_ids": manifest.get("splits", {}).get("held_out"),
            "public_case_ids": manifest.get("splits", {}).get("public"),
            "schema": "schemas/agentsecbench-submission.schema.json",
            "participation_guide": "PARTICIPATION.md",
        },
    )
    schema_src = repo_root() / "schemas" / "agentsecbench-submission.schema.json"
    if schema_src.is_file():
        shutil.copy2(schema_src, output_dir / "agentsecbench-submission.schema.json")
    for name in ("PARTICIPATION.md", "EVALUATION-PROTOCOL.md"):
        src = llm_cases_root() / name
        if src.is_file():
            shutil.copy2(src, output_dir / name)
    return {"ok": True, "output_dir": str(output_dir), "case_count": len(cards)}
