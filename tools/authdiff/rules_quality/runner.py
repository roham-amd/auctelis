"""Run authdiff rule-quality cases.

Separate from AgentSecBench LLM scoring and from the tooling corpus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from authdiff.paths import repo_root
from authdiff.security.engine import run_security_scan
from authdiff.security.scan import run_scan
from authdiff.versioning import load_versions


def rules_root() -> Path:
    return repo_root() / "tests" / "rules"


def _load_cases() -> list[dict[str, Any]]:
    cases_dir = rules_root() / "cases"
    if not cases_dir.is_dir():
        return []
    cases: list[dict[str, Any]] = []
    for path in sorted(cases_dir.glob("RULE-*.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


def _matching_findings(scan_findings: list[Any], rule_id: str) -> list[Any]:
    return [f for f in scan_findings if f.rule_id == rule_id]


def _check_case(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fixture_rel = case.get("fixture")
    rule_id = str(case.get("rule_id") or "")
    if not fixture_rel or not rule_id:
        return ["missing fixture or rule_id"]
    fixture = rules_root() / fixture_rel
    if not fixture.is_dir():
        return [f"fixture directory missing: {fixture_rel}"]

    scan = run_security_scan(fixture)
    matched = _matching_findings(scan.findings, rule_id)
    expect = case.get("expect") or {}

    if expect.get("rule_fired") is True and not matched:
        errors.append(f"expected {rule_id} to fire")
    if expect.get("rule_fired") is False and matched:
        errors.append(f"expected {rule_id} not to fire, got {len(matched)} hit(s)")

    for other in case.get("forbid_rule_ids") or []:
        if any(f.rule_id == other for f in scan.findings):
            errors.append(f"forbidden rule {other} fired")

    if matched:
        # When adapters emit duplicate surfaces, prefer a finding that already
        # satisfies the expected class/severity so inventory duplicates do not
        # fail a positive case that also produced the stronger hit.
        finding = matched[0]
        want_class = expect.get("finding_class")
        want_sev = expect.get("severity")
        if want_class or want_sev:
            allowed_c = {want_class} if isinstance(want_class, str) else set(want_class or [])
            allowed_s = {want_sev} if isinstance(want_sev, str) else set(want_sev or [])
            for candidate in matched:
                if allowed_c and candidate.finding_class not in allowed_c:
                    continue
                if allowed_s and candidate.severity not in allowed_s:
                    continue
                finding = candidate
                break
        allowed_classes = expect.get("finding_class")
        if allowed_classes:
            allowed = (
                {allowed_classes} if isinstance(allowed_classes, str) else set(allowed_classes)
            )
            if finding.finding_class not in allowed:
                errors.append(f"finding_class {finding.finding_class} not in {sorted(allowed)}")
        allowed_sev = expect.get("severity")
        if allowed_sev:
            allowed = {allowed_sev} if isinstance(allowed_sev, str) else set(allowed_sev)
            if finding.severity not in allowed:
                errors.append(f"severity {finding.severity} not in {sorted(allowed)}")
        allowed_conf = expect.get("confidence")
        if allowed_conf:
            allowed = {allowed_conf} if isinstance(allowed_conf, str) else set(allowed_conf)
            if finding.confidence not in allowed:
                errors.append(f"confidence {finding.confidence} not in {sorted(allowed)}")
        forbid_classes = set(expect.get("forbid_finding_class") or [])
        # Forbid applies to *any* matched finding so a stronger duplicate cannot hide.
        if any(f.finding_class in forbid_classes for f in matched):
            bad = next(f for f in matched if f.finding_class in forbid_classes)
            errors.append(f"finding_class {bad.finding_class} is forbidden")

    # Harmless / negative cases must never produce SECURITY_FINDING for the target rule,
    # and optional global guard against any SECURITY_FINDING when requested.
    if expect.get("no_security_findings"):
        security = [f for f in scan.findings if f.finding_class == "SECURITY_FINDING"]
        if security:
            errors.append(
                "expected no SECURITY_FINDING, got: "
                + ", ".join(f"{f.rule_id}/{f.finding_id}" for f in security)
            )

    fail_on = expect.get("fail_on")
    if fail_on:
        _scan, _payload, code = run_scan(
            fixture, output_dir=fixture / "authdiff-out-test", fail_on=fail_on
        )
        expected_code = int(expect.get("fail_on_exit_code", 0))
        if code != expected_code:
            errors.append(f"fail_on={fail_on} exit {code}, expected {expected_code}")

    return errors


def run_rule_quality() -> dict[str, Any]:
    cases = _load_cases()
    results: list[dict[str, Any]] = []
    failed = 0
    for case in cases:
        errors = _check_case(case)
        ok = not errors
        if not ok:
            failed += 1
        results.append(
            {
                "id": case.get("id"),
                "rule_id": case.get("rule_id"),
                "variant": case.get("variant"),
                "ok": ok,
                "errors": errors,
                "notes": case.get("notes") or [],
            }
        )
    pack_ver = load_versions().get("rule_quality_pack", "1.0.0")
    return {
        "pack": "authdiff rule-quality",
        "pack_version": pack_ver,
        "mode": "deterministic_rule_fixtures",
        "total": len(cases),
        "failed": failed,
        "passed": len(cases) - failed,
        "results": results,
        "limitations": [
            "Scores deterministic Guard rules only — not AI auditor detection quality.",
            "Absence of SECURITY_FINDING is not proof of safety under incomplete coverage.",
        ],
    }
