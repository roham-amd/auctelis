"""Semantic validation of audit reports (JSON Schema cannot express these)."""

from __future__ import annotations

from typing import Any

from auctelis_devtools.semantic import validate_semantics


def _valid_report() -> dict[str, Any]:
    return {
        "components": [{"component_id": "C-1", "evidence_ids": ["E-1"]}],
        "findings": [
            {
                "finding_id": "F-1",
                "severity": "HIGH",
                "evidence_ids": ["E-1"],
                "affected_component_ids": ["C-1"],
            }
        ],
        "evidence_registry": [
            {
                "evidence_id": "E-1",
                "component_id": "C-1",
                "retrieval_date_utc": "2026-11-18T00:00:00Z",
                "artifact_digest": "a" * 64,
            }
        ],
        "findings_count": {
            "critical": 0,
            "high": 1,
            "medium": 0,
            "low": 0,
            "informational": 0,
        },
        "component_inventory": {"total_discovered": 1},
    }


def _codes(report: dict[str, Any]) -> set[str]:
    return {issue.code for issue in validate_semantics(report).issues}


def test_valid_report_passes():
    result = validate_semantics(_valid_report())
    assert result.ok is True
    assert result.issues == []


def test_duplicate_ids_are_rejected():
    report = _valid_report()
    report["components"].append({"component_id": "C-1"})
    report["evidence_registry"].append({"evidence_id": "E-1"})
    report["findings"].append({"finding_id": "F-1", "severity": "HIGH"})
    report["findings_count"] = {"critical": 0, "high": 2, "medium": 0, "low": 0, "informational": 0}
    assert "DUPLICATE_ID" in _codes(report)


def test_dangling_component_and_evidence_refs():
    report = _valid_report()
    report["evidence_registry"][0]["component_id"] = "C-missing"
    report["components"][0]["evidence_ids"] = ["E-missing"]
    report["components"][0]["finding_ids"] = ["F-missing"]
    report["findings"][0]["affected_component_ids"] = ["C-missing"]
    assert "DANGLING_COMPONENT_REF" in _codes(report)
    assert "DANGLING_EVIDENCE_REF" in _codes(report)
    assert "DANGLING_FINDING_REF" in _codes(report)


def test_invalid_timestamp_and_digest():
    report = _valid_report()
    report["evidence_registry"][0]["retrieval_date_utc"] = "2026-11-18"
    report["evidence_registry"][0]["artifact_digest"] = "not a digest!"
    codes = _codes(report)
    assert "INVALID_TIMESTAMP" in codes
    assert "INVALID_DIGEST" in codes


def test_findings_count_buckets_and_mismatch():
    report = _valid_report()
    report["findings_count"] = {"critical": 0, "high": 2}
    codes = _codes(report)
    assert "MISSING_COUNT" in codes
    assert "FINDINGS_COUNT_MISMATCH" in codes


def test_confirmed_finding_requires_evidence():
    report = _valid_report()
    report["findings"][0]["evidence_label"] = "CONFIRMED"
    report["findings"][0]["evidence_ids"] = []
    report["components"][0]["evidence_ids"] = []
    assert "UNSUPPORTED_CLAIM" in _codes(report)


def test_runtime_mislabel_and_inventory_count():
    report = _valid_report()
    report["trust_chain"] = {"runtime_behavior_tested": True}
    report["component_inventory"]["total_discovered"] = 0
    codes = _codes(report)
    assert "RUNTIME_MISLABEL" in codes
    assert "INVENTORY_COUNT" in codes


def test_hard_gate_evidence_refs():
    report = _valid_report()
    report["component_hard_gates"] = [{"gate_id": "G-1", "evidence_ids": ["E-missing"]}]
    report["cross_component_hard_gates"] = [{"gate_id": "G-2", "evidence_ids": ["E-missing"]}]
    report["components"][0]["hard_gates"] = [{"evidence_ids": ["E-missing"]}]
    result = validate_semantics(report)
    dangling = [issue for issue in result.issues if issue.code == "DANGLING_EVIDENCE_REF"]
    assert len(dangling) == 3
