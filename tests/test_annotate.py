from pathlib import Path

from auctelis.export.annotate import (
    iter_annotation_targets,
    render_github_annotations,
    render_text_annotations,
)
from auctelis.jsonio import read_json
from auctelis.security.scan import run_scan


def test_github_annotations_from_live_scan(tmp_path: Path) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "rules"
        / "fixtures"
        / "rule-002-positive-broad"
    )
    scan, _payload, _code = run_scan(fixture, output_dir=tmp_path / "out")
    doc = scan.to_findings_doc()
    text = render_github_annotations(doc)
    assert "::error" in text or "::warning" in text
    assert "F-" in text


def test_text_annotations_non_empty(tmp_path: Path) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "rules"
        / "fixtures"
        / "rule-002-positive-broad"
    )
    scan, _payload, _code = run_scan(fixture, output_dir=tmp_path / "out")
    text = render_text_annotations(scan.to_findings_doc())
    assert "SECURITY_FINDING" in text or "EXPOSURE" in text


def test_annotations_skip_findings_without_evidence_ids() -> None:
    doc = {
        "findings": [
            {
                "finding_id": "F-NOEV",
                "rule_id": "AUCTELIS-RULE-003",
                "title": "no evidence",
                "severity": "HIGH",
                "finding_class": "EXPOSURE",
                "evidence_ids": [],
                "description": "should not annotate",
            }
        ],
        "evidence_registry": [],
    }
    assert iter_annotation_targets(doc) == []


def test_sample_findings_still_annotatable_when_present() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "guard-scan" / "findings.json"
    if not path.is_file():
        return
    doc = read_json(path)
    # Historical samples may lag; only assert shape when gateable findings exist.
    targets = iter_annotation_targets(doc)
    if any(
        f.get("finding_class") in {"SECURITY_FINDING", "EXPOSURE"} and f.get("evidence_ids")
        for f in doc.get("findings") or []
    ):
        assert targets
