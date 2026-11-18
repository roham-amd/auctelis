from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from auctelis.build import validate_json_schema_document
from auctelis.paths import canonical_schema_path, repo_root
from auctelis.semantic import SemanticResult, validate_semantics


def _load_graph_analysis() -> Any:
    """Import research graph helpers (source checkout; not in the product wheel)."""
    try:
        from auctelis_research.graph import analysis as graph_analysis

        return graph_analysis
    except ImportError:
        pass
    import auctelis as _pkg

    tools_dir = str(Path(_pkg.__file__).resolve().parents[1])
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    try:
        from auctelis_research.graph import analysis as graph_analysis
    except ImportError as exc:
        raise SystemExit(
            "Graph validation requires auctelis_research (source checkout / auctelis-dev)."
        ) from exc
    return graph_analysis


def load_report(path: Path) -> dict[str, Any]:
    """Load a JSON report object, failing closed with an actionable message."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Cannot read report {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in report {path}: {exc}") from exc
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


def validate_graph_file(path: Path, *, semantic: bool = True) -> Any:
    graph = _load_graph_analysis()
    schema_path = repo_root() / "schemas" / "ecosystem-graph.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Cannot read graph {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in graph {path}: {exc}") from exc
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errors:
        msgs = "\n".join(f"  - {list(e.path)}: {e.message}" for e in errors[:20])
        raise SystemExit(f"Graph schema validation failed for {path}:\n{msgs}")
    if not semantic:
        return graph.GraphSemanticResult(ok=True)
    return graph.validate_graph_semantics(doc)


def analyze_graph_paths(path: Path) -> list[Any]:
    graph = _load_graph_analysis()
    doc = json.loads(path.read_text(encoding="utf-8"))
    start_kinds, end_kinds = graph.DEFAULT_UNTRUSTED_TO_EXTERNAL
    paths: list[Any] = list(graph.find_paths(doc, start_kinds=start_kinds, end_kinds=end_kinds))
    return paths
