"""Week 4: Atlas precision ledger + labeling template schema."""

from __future__ import annotations

import json
from pathlib import Path

from authdiff.rules_quality.runner import run_rule_quality

_REPO = Path(__file__).resolve().parents[1]


def test_precision_json_schema():
    path = _REPO / "docs" / "atlas" / "precision.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "authdiff.atlas.precision.v1"
    assert "policy" in data and "rules" in data
    for rule in data["rules"]:
        assert rule["rule_id"].startswith("AUTHDIFF-RULE-")
        assert int(rule.get("labeled_n") or 0) >= 0
        assert rule.get("precision") in (None, 0) or int(rule.get("labeled_n") or 0) > 0


def test_labeling_template_schema():
    path = _REPO / "docs" / "atlas" / "labeling-template.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "authdiff.atlas.labeling.v1"
    assert "finding_label" in data
    assert data["finding_label"]["label"] == "pending"


def test_rules_quality_cli_helper():
    summary = run_rule_quality()
    assert summary["failed"] == 0
    assert summary["total"] >= 1
