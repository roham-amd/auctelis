from pathlib import Path

from auctelis.corpus.runner import run_corpus
from auctelis.inventory.collector import collect_inventory, inventory_to_json
from auctelis.inventory.limits import CollectorLimits
from auctelis.validate_report import analyze_graph_paths


def test_dependency_pins_consistent():
    from auctelis.build import check_dependency_pins, check_requires_python

    check_requires_python()
    actions = check_dependency_pins()
    assert any("jsonschema" in a for a in actions)
    assert any("uv.lock" in a for a in actions)


def test_deps_outdated_report_structure(monkeypatch):
    from auctelis import deps

    pins = deps.parse_lock_pins()
    assert "jsonschema" in pins
    assert deps.lock_path().is_file()

    def fake_latest(name: str, *, timeout: float = 20.0) -> str:
        return pins.get(name, pins.get(next(k for k in pins if k.lower() == name.lower())))

    monkeypatch.setattr(deps, "fetch_latest_version", fake_latest)
    report = deps.outdated_report()
    assert report["outdated_count"] == 0
    assert report["requires_python_expected"] == ">=3.12"
    assert report["checked"] == len(pins)
    assert report["lock"] == "tools/uv.lock"


def test_corpus_harness_passes():
    summary = run_corpus()
    assert summary["failed"] == 0, summary


def test_attack_path_search():
    graph = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "validation"
        / "positive"
        / "attack-path-graph.json"
    )
    paths = analyze_graph_paths(graph)
    assert len(paths) >= 1


def test_inventory_finds_skill_and_mcp():
    root = (
        Path(__file__).resolve().parents[1] / "tests" / "corpus" / "fixtures" / "benign-skill-mcp"
    )
    inv = collect_inventory(root)
    names = {c["name"] for c in inv.components}
    assert "benign-readonly-helper" in names
    assert "filesystem-readonly" in names
    payload = inventory_to_json(inv)
    assert "coverage" in payload
    assert "adapter_matrix" in payload["coverage"]


def test_preflight_graph_helpers(tmp_path: Path):
    from auctelis.jsonio import write_json
    from auctelis.preflight import build_audit_context_md, inventory_to_graph, run_preflight
    from auctelis.validate_report import validate_graph_file

    root = (
        Path(__file__).resolve().parents[1] / "tests" / "corpus" / "fixtures" / "benign-skill-mcp"
    )
    inv = collect_inventory(root)
    graph = inventory_to_graph(inv)
    out = tmp_path / "ecosystem-graph.json"
    write_json(out, graph)
    result = validate_graph_file(out)
    assert result.ok, [f"{i.code}: {i.message}" for i in result.issues]
    ctx = build_audit_context_md(inv, commit="deadbeef")
    assert "NOT VERIFIED" in ctx
    assert "deadbeef" in ctx
    pf = run_preflight(root, output_dir=tmp_path / "pf-out")
    assert pf["component_count"] >= 2
    assert (tmp_path / "pf-out" / "inventory.json").is_file()


def test_github_workflow_adapter(tmp_path: Path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(
        "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    inv = collect_inventory(tmp_path)
    types = {c["type"] for c in inv.components}
    assert "CI Workflow" in types


def test_mcp_example_and_server_source(tmp_path: Path):
    cursor = tmp_path / ".cursor"
    cursor.mkdir()
    (cursor / "mcp_example.json").write_text(
        '{"mcpServers": {"demo": {"command": "npx", "args": ["-y", "pkg@1.0.0"]}}}',
        encoding="utf-8",
    )
    (tmp_path / "server_mcp.py").write_text(
        "import mcp\n# mcp server stub\n",
        encoding="utf-8",
    )
    inv = collect_inventory(tmp_path, limits=CollectorLimits(max_files=50))
    types = {c["type"] for c in inv.components}
    assert "MCP Server Registration" in types
