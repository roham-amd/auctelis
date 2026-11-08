"""AgentSecBench runner.

Validates deterministic discovery and Guard rule expectations. Records
placeholders for LLM finding-quality scores. It does **not** invoke models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from authdiff.inventory.collector import collect_inventory
from authdiff.paths import repo_root
from authdiff.security.engine import run_security_scan
from authdiff.versioning import load_versions


def benchmark_root() -> Path:
    return repo_root() / "tests" / "benchmark"


def _load_cases() -> list[dict[str, Any]]:
    cases_dir = benchmark_root() / "cases"
    if not cases_dir.is_dir():
        return []
    cases: list[dict[str, Any]] = []
    for path in sorted(cases_dir.glob("BENCH-*.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


def _check_inventory_expectations(
    case: dict[str, Any], components: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    expected = case.get("expect_inventory") or {}
    types = {str(c.get("type")) for c in components}
    names = {str(c.get("name")) for c in components}
    for req in expected.get("types_any_of") or []:
        if req not in types:
            errors.append(f"missing component type {req}")
    for req in expected.get("names_any_of") or []:
        if req not in names:
            errors.append(f"missing component name {req}")
    min_count = expected.get("min_components")
    if min_count is not None and len(components) < int(min_count):
        errors.append(f"expected >= {min_count} components, got {len(components)}")
    return errors


def _check_rule_expectations(case: dict[str, Any], fixture: Path) -> list[str]:
    expected_rules = case.get("expect_rule_ids") or []
    forbidden_rules = case.get("forbid_rule_ids") or []
    if not expected_rules and not forbidden_rules:
        return []
    scan = run_security_scan(fixture)
    found = {f.rule_id for f in scan.findings}
    errors: list[str] = []
    for rule_id in expected_rules:
        if rule_id not in found:
            errors.append(f"expected Guard rule {rule_id} not fired")
    for rule_id in forbidden_rules:
        if rule_id in found:
            errors.append(f"forbidden Guard rule {rule_id} fired")
    return errors


def run_benchmark() -> dict[str, Any]:
    cases = _load_cases()
    results: list[dict[str, Any]] = []
    failed = 0
    for case in cases:
        case_id = case.get("id", "unknown")
        fixture_rel = case.get("fixture")
        if not fixture_rel:
            results.append(
                {
                    "id": case_id,
                    "ok": False,
                    "errors": ["missing fixture"],
                    "llm_scoring": "not_run",
                }
            )
            failed += 1
            continue
        fixture = benchmark_root() / fixture_rel
        inv = collect_inventory(fixture)
        errors = _check_inventory_expectations(case, inv.components)
        errors.extend(_check_rule_expectations(case, fixture))
        ok = not errors
        if not ok:
            failed += 1
        results.append(
            {
                "id": case_id,
                "title": case.get("title"),
                "family": case.get("family"),
                "ok": ok,
                "errors": errors,
                "components_found": len(inv.components),
                "llm_scoring": case.get("llm_scoring", "deferred"),
                "ground_truth_findings": case.get("ground_truth_findings") or [],
                "notes": case.get("notes") or [],
            }
        )

    bench_ver = load_versions().get("agent_benchmark", "0.2.0")
    return {
        "benchmark_version": bench_ver,
        "benchmark_name": "AgentSecBench",
        "mode": "deterministic_expectations_and_guard_rules",
        "total": len(cases),
        "failed": failed,
        "passed": len(cases) - failed,
        "results": results,
        "limitations": [
            "LLM/agent finding precision and recall are not measured in this run.",
            "Populate model runners + expert-reviewed ground_truth_findings to score detection quality.",
            "Do not cite inventory/rule fixture pass rates as AI auditor accuracy.",
        ],
    }
