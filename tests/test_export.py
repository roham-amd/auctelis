import json
from pathlib import Path

from authdiff.audit_diff import diff_reports
from authdiff.export.sarif import report_to_sarif


def test_sarif_export_from_sample():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "validation"
        / "positive"
        / "sample-audit-summary.json"
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    sarif = report_to_sarif(doc)
    assert len(sarif["runs"][0]["results"]) >= 1


def test_audit_diff_empty_when_same():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "validation"
        / "positive"
        / "sample-audit-summary.json"
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    d = diff_reports(doc, doc)
    assert d["summary"]["findings_added"] == 0
