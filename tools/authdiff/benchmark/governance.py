"""Dataset governance: checksums, splits, pinned evaluation metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from authdiff.paths import repo_root
from authdiff.supply_chain.digest import sha256_file as digest_hex
from authdiff.versioning import load_versions, package_version, product_version

SplitName = Literal["public", "held_out", "all"]


def llm_cases_root() -> Path:
    return repo_root() / "tests" / "benchmark" / "llm"


def dataset_manifest_path() -> Path:
    return llm_cases_root() / "DATASET.json"


def sha256_file(path: Path) -> str:
    """Checksum with ``sha256:`` prefix (dataset manifest convention)."""
    return f"sha256:{digest_hex(path)}"


def compute_case_checksums() -> dict[str, str]:
    cases_dir = llm_cases_root() / "cases"
    out: dict[str, str] = {}
    for path in sorted(cases_dir.glob("LLM-*.json")):
        out[path.name] = sha256_file(path)
    return out


def verify_dataset_integrity(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = (
        manifest
        if manifest is not None
        else json.loads(dataset_manifest_path().read_text(encoding="utf-8"))
    )
    expected = dict(manifest.get("case_checksums") or {})
    actual = compute_case_checksums()
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatched = sorted(
        name for name in set(expected) & set(actual) if expected[name] != actual[name]
    )
    ok = not missing and not unexpected and not mismatched
    return {
        "ok": ok,
        "dataset_version": manifest.get("dataset_version"),
        "rubric_version": manifest.get("rubric_version"),
        "case_count_expected": len(expected),
        "case_count_actual": len(actual),
        "missing": missing,
        "unexpected": unexpected,
        "mismatched": mismatched,
        "scorer_package_version": package_version(),
        "product_version": product_version(),
        "agent_benchmark_llm": load_versions().get("agent_benchmark_llm"),
    }


def case_split(case_id: str, manifest: dict[str, Any]) -> str:
    public = set(manifest.get("splits", {}).get("public") or [])
    held = set(manifest.get("splits", {}).get("held_out") or [])
    if case_id in held:
        return "held_out"
    if case_id in public:
        return "public"
    return "unassigned"


def filter_cases_by_split(
    cases: list[dict[str, Any]],
    *,
    split: SplitName,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    if split == "all":
        return cases
    return [c for c in cases if case_split(str(c.get("id")), manifest) == split]


def evaluation_pin(*, split: str, submissions: str | None) -> dict[str, Any]:
    """Traceability record for a reproducible evaluation run."""
    manifest = json.loads(dataset_manifest_path().read_text(encoding="utf-8"))
    integrity = verify_dataset_integrity(manifest)
    return {
        "pin_version": "1.0",
        "dataset_version": manifest.get("dataset_version"),
        "rubric_version": manifest.get("rubric_version"),
        "submission_schema": manifest.get("submission_schema"),
        "split": split,
        "submissions": submissions,
        "product_version": product_version(),
        "package_version": package_version(),
        "agent_benchmark_llm": load_versions().get("agent_benchmark_llm"),
        "dataset_integrity_ok": integrity["ok"],
        "case_checksums": manifest.get("case_checksums"),
    }
