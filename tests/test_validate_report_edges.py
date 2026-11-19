"""Report/graph validation error paths and honest semantic results."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auctelis_devtools.validate_report import (
    load_report,
    validate_graph_file,
    validate_report_file,
)

_ROOT = Path(__file__).resolve().parents[1]


def test_load_report_missing_file_fails_closed(tmp_path: Path):
    with pytest.raises(SystemExit, match="Cannot read report"):
        load_report(tmp_path / "missing.json")


def test_load_report_invalid_json_fails_closed(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{nope", encoding="utf-8")
    with pytest.raises(SystemExit, match="Invalid JSON"):
        load_report(path)


def test_load_report_requires_object(tmp_path: Path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(SystemExit, match="Expected JSON object"):
        load_report(path)


def test_negative_fixture_is_not_semantically_ok():
    path = _ROOT / "tests" / "validation" / "negative" / "duplicate-component-id.json"
    result = validate_report_file(path)
    assert result.ok is False
    assert result.issues


def test_semantic_false_skips_semantic_result():
    path = _ROOT / "tests" / "validation" / "negative" / "duplicate-component-id.json"
    result = validate_report_file(path, semantic=False)
    assert result.ok is True


def test_validate_graph_missing_file_fails_closed(tmp_path: Path):
    with pytest.raises(SystemExit, match="Cannot read graph"):
        validate_graph_file(tmp_path / "missing.json")


def test_validate_graph_invalid_json_fails_closed(tmp_path: Path):
    path = tmp_path / "graph.json"
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(SystemExit, match="Invalid JSON"):
        validate_graph_file(path)


def test_validate_graph_schema_rejects_empty_document(tmp_path: Path):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(SystemExit, match="Graph schema validation failed"):
        validate_graph_file(path)


def test_validate_graph_semantic_skip_returns_ok(tmp_path: Path):
    path = _ROOT / "tests" / "validation" / "positive" / "minimal-graph.json"
    result = validate_graph_file(path, semantic=False)
    assert result.ok is True
