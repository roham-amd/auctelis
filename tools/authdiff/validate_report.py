from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from authdiff.build import validate_json_schema_document
from authdiff.graph.analysis import (
    DEFAULT_UNTRUSTED_TO_EXTERNAL,
    GraphSemanticResult,
    find_paths,
    validate_graph_semantics,
)
from authdiff.paths import canonical_schema_path, repo_root
from authdiff.semantic import SemanticResult, validate_semantics


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected JSON object in {path}, got {type(data).__name__}")
    return data


def validate_report_file(path: Path, *, semantic: bool = True) -> SemanticResult:
    validate_json_schema_document()
    schema = json.loads(canonical_schema_path().read_text(encoding="utf-8"))
    doc = load_report(path)
    validator = Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if schema_errors:
        msgs = "\n".join(f"  - {list(e.path)}: {e.message}" for e in schema_errors[:20])
        raise SystemExit(f"JSON Schema validation failed for {path}:\n{msgs}")

    if not semantic:
        return SemanticResult(ok=True)

    return validate_semantics(doc)


def validate_graph_file(path: Path, *, semantic: bool = True) -> GraphSemanticResult:
    schema_path = repo_root() / "schemas" / "ecosystem-graph.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    doc = json.loads(path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errors:
        msgs = "\n".join(f"  - {list(e.path)}: {e.message}" for e in errors[:20])
        raise SystemExit(f"Graph schema validation failed for {path}:\n{msgs}")
    if not semantic:
        return GraphSemanticResult(ok=True)
    return validate_graph_semantics(doc)


def analyze_graph_paths(path: Path) -> list:
    doc = json.loads(path.read_text(encoding="utf-8"))
    start_kinds, end_kinds = DEFAULT_UNTRUSTED_TO_EXTERNAL
    return find_paths(doc, start_kinds=start_kinds, end_kinds=end_kinds)
