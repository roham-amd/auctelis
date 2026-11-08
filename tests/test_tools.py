import json
from pathlib import Path

from authdiff.audit import run_audit
from authdiff.benchmark.runner import run_benchmark
from authdiff.corpus.runner import run_corpus
from authdiff.inventory.collector import collect_inventory, inventory_to_json
from authdiff.inventory.limits import CollectorLimits
from authdiff.preflight import run_preflight
from authdiff.validate_report import analyze_graph_paths


def test_dependency_pins_consistent():
    from authdiff.build import check_dependency_pins, check_requires_python

    check_requires_python()
    actions = check_dependency_pins()
    assert any("jsonschema" in a for a in actions)
    assert any("uv.lock" in a for a in actions)


def test_deps_outdated_report_structure(monkeypatch):
    from authdiff import deps

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


def test_preflight_writes_outputs(tmp_path: Path):
    from authdiff.validate_report import validate_graph_file

    root = (
        Path(__file__).resolve().parents[1] / "tests" / "corpus" / "fixtures" / "benign-skill-mcp"
    )
    out = tmp_path / "authdiff-out"
    result = run_preflight(root, output_dir=out)
    assert result["component_count"] >= 2
    assert (out / "inventory.json").is_file()
    assert (out / "ecosystem-graph.json").is_file()
    assert (out / "audit-context.md").is_file()
    assert "NOT VERIFIED" in result["summary"]
    graph = validate_graph_file(out / "ecosystem-graph.json")
    assert graph.ok, [f"{i.code}: {i.message}" for i in graph.issues]


def test_audit_standard_writes_profile(tmp_path: Path):
    root = (
        Path(__file__).resolve().parents[1] / "tests" / "corpus" / "fixtures" / "benign-skill-mcp"
    )
    out = tmp_path / "authdiff-out"
    result = run_audit(root, profile="standard", output_dir=out)
    assert result["profile"] == "standard"
    assert (out / "profile.json").is_file()
    assert (out / "audit-summary.md").is_file()
    ctx = (out / "audit-context.md").read_text(encoding="utf-8")
    assert "Audit profile" in ctx
    assert "Suggested modules" in ctx


def test_audit_deployment_worksheet(tmp_path: Path):
    root = (
        Path(__file__).resolve().parents[1] / "tests" / "corpus" / "fixtures" / "benign-skill-mcp"
    )
    out = tmp_path / "deploy-out"
    run_audit(root, profile="deployment", output_dir=out)
    assert (out / "deployment-worksheet.md").is_file()


def test_benchmark_harness_passes():
    summary = run_benchmark()
    assert summary["failed"] == 0, summary


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
        json.dumps(
            {
                "mcpServers": {
                    "demo": {
                        "command": "uv",
                        "args": ["run", "mcp/skills_mcp.py"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    mcp_dir = tmp_path / "mcp"
    mcp_dir.mkdir()
    (mcp_dir / "skills_mcp.py").write_text(
        "from fastmcp import FastMCP\nmcp = FastMCP(name='demo')\n",
        encoding="utf-8",
    )
    inv = collect_inventory(tmp_path)
    types = {c["type"] for c in inv.components}
    names = {c["name"] for c in inv.components}
    assert "MCP Server Registration" in types
    assert "MCP Server Implementation" in types
    assert "demo" in names
    assert "skills_mcp" in names


def test_inventory_skips_oversize_before_read(tmp_path: Path):
    huge = tmp_path / "SKILL.md"
    huge.write_bytes(b"x" * 5000)
    inv = collect_inventory(tmp_path, limits=CollectorLimits(max_file_bytes=100))
    assert inv.components == []
    assert any(e.get("type") == "parse_skipped_size" for e in inv.parser_events)
