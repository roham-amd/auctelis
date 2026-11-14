"""The 54-rule-case manifest is a live regression corpus.

Each JSON under ``tests/rules/cases`` names a fixture and the expected firing,
class, severity, and evidence strength. This test makes the manifests a real
gate instead of an unused scaffold.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auctelis.security.scan import run_scan

_ROOT = Path(__file__).resolve().parents[1]
_CASES = sorted((_ROOT / "tests" / "rules" / "cases").glob("*.json"))
_EVIDENCE_STRENGTHS = {"LITERAL_CONFIG", "INFERRED_HINT", "NAME_MARKER"}


@pytest.mark.parametrize("case_path", _CASES, ids=lambda path: path.stem)
def test_rule_case_manifest(case_path: Path, tmp_path: Path):
    case = json.loads(case_path.read_text(encoding="utf-8"))
    fixture = _ROOT / "tests" / "rules" / case["fixture"]
    assert fixture.is_dir(), f"fixture missing: {case['fixture']}"
    scan, _payload, _code = run_scan(
        fixture,
        output_dir=tmp_path / case["id"],
        fail_on="never",
    )
    rule_id = case["rule_id"]
    expected = case.get("expect") or {}
    matching = [finding for finding in scan.findings if finding.rule_id == rule_id]
    fired = bool(matching)

    assert fired is bool(expected.get("rule_fired", True)), (
        f"{case['id']}: rule {rule_id} fired={fired}; "
        f"all={sorted({f.rule_id for f in scan.findings})}"
    )
    if not fired:
        return

    if expected.get("finding_class"):
        assert any(f.finding_class == expected["finding_class"] for f in matching)
    if expected.get("severity"):
        assert any(f.severity == expected["severity"] for f in matching)
    expected_confidence = expected.get("confidence")
    if expected_confidence in _EVIDENCE_STRENGTHS:
        assert any(f.evidence_strength == expected_confidence for f in matching)
    elif expected_confidence:
        assert any(f.confidence == expected_confidence for f in matching)

    for forbidden in expected.get("forbid_finding_class") or []:
        assert not any(f.finding_class == forbidden for f in scan.findings), (
            f"{case['id']}: forbidden class {forbidden} present"
        )
