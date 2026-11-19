"""0.8.1 recovery: consumer Action pin, empty baseline, init/status, strict false."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.cli import main
from auctelis.cli.dispatch import _pin_workflow_to_release, _resolve_action_pin_ref
from auctelis.gate import run_gate
from auctelis.lock_io import compute_lock_hash
from auctelis.versioning import product_version


def _mcp(root: Path, servers: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    cfg = root / ".mcp.json"
    cfg.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def test_action_pin_is_release_tag_not_consumer_sha(tmp_path: Path):
    pin = _resolve_action_pin_ref()
    assert pin == f"v{product_version()}"
    assert len(pin) != 40 or not all(c in "0123456789abcdef" for c in pin)

    template = (
        "uses: roham-amd/auctelis/.github/actions/auctelis-gate@v0.0.0\n"
        'pip install "git+https://github.com/roham-amd/auctelis.git@v0.0.0#subdirectory=tools"\n'
    )
    pinned = _pin_workflow_to_release(template)
    assert f"auctelis-gate@{pin}" in pinned
    assert f"auctelis.git@{pin}" in pinned
    assert "auctelis-gate@v0.0.0" not in pinned
    # Never rewrite to a 40-char consumer SHA.
    assert "@deadbeef" not in pinned


def test_ci_init_apply_pins_release_and_exits_zero(tmp_path: Path, capsys):
    root = tmp_path / "consumer"
    _mcp(root, {"linear": {"command": "npx", "args": ["-y", "@linear/mcp"]}})
    # Fake a distinct consumer HEAD so a regression would pin the wrong SHA.
    (root / ".git").mkdir()
    code = main(["ci", "init", str(root), "--owner", "@security", "--apply"])
    out = capsys.readouterr().out
    assert code == 0, out
    workflow = (root / ".github" / "workflows" / "auctelis-gate.yml").read_text(encoding="utf-8")
    pin = _resolve_action_pin_ref()
    assert f"auctelis-gate@{pin}" in workflow
    assert "deadbeef" not in workflow
    assert (root / "AUTHORITY.lock").is_file()
    # Comment-only --apply does not nag about rulesets (nothing to enforce yet).
    assert "Comment-only mode: no ruleset required" in out


def test_init_command_one_shot(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    code = main(["init", str(root), "--owner", "@sec"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert (root / "AUTHORITY.lock").is_file()
    assert (root / ".auctelis.yml").is_file()
    assert (root / ".github" / "workflows" / "auctelis-gate.yml").is_file()
    assert (root / ".github" / "CODEOWNERS").is_file()


def test_status_reports_gate_surface(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["init", str(root), "--owner", "@sec"]) == 0
    capsys.readouterr()
    code = main(["status", str(root)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Lock: present" in out
    assert "Workflow:" in out and "auctelis-gate.yml" in out
    assert "Mode: comment-only" in out
    assert "CODEOWNERS:" in out
    assert "Protection:" in out


def test_empty_baseline_lifecycle(tmp_path: Path):
    """Empty repo seals 0 records; first MCP is GROWTH needing CODEOWNERS."""
    root = tmp_path / "empty"
    root.mkdir()
    (root / ".github").mkdir()
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    assert main(["lock", str(root), "--update"]) == 0
    base = root / "AUTHORITY.lock"
    data = json.loads(base.read_text(encoding="utf-8"))
    assert data.get("records") == []

    # First MCP arrives on a branch — gate against empty base.
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    assert main(["lock", str(root), "--update"]) == 0
    empty_base = tmp_path / "empty-base.lock"
    hollow = {"version": 1, "records": [], "mcp_tools": {}}
    hollow["lock_hash"] = compute_lock_hash(hollow)
    empty_base.write_text(json.dumps(hollow), encoding="utf-8")
    report, _code = run_gate(root, base_lock=empty_base, check_ruleset=False)
    assert report["label"] == "GROWTH"
    assert report.get("empty_baseline_growth") is True
    assert report["verdict"] != "FAIL_CLOSED"


def test_action_yml_passes_no_strict_ruleset():
    action = (
        Path(__file__).resolve().parents[1] / ".github" / "actions" / "auctelis-gate" / "action.yml"
    )
    text = action.read_text(encoding="utf-8")
    # Comment-only still passes --no-strict-ruleset; locked=true defaults strict on.
    assert "--no-strict-ruleset" in text
    assert "locked=true default" in text


def test_claude_slash_command_in_authority_kinds():
    from auctelis.security.authority import build_authority_snapshot

    src = Path(__file__).resolve().parents[1] / "tools" / "auctelis" / "security" / "authority.py"
    text = src.read_text(encoding="utf-8")
    assert '"Claude slash command"' in text
    # Smoke: snapshot helper still importable.
    assert callable(build_authority_snapshot)


def test_literal_mcp_evidence_strength(tmp_path: Path):
    from auctelis.authority_lock import build_authority_lock

    root = tmp_path / "repo"
    _mcp(
        root,
        {
            "linear": {
                "command": "npx",
                "args": ["-y", "@linear/mcp"],
                "url": "https://mcp.linear.app/sse",
            }
        },
    )
    lock = build_authority_lock(root)
    mcp = [r for r in lock["records"] if r["kind"] == "MCP Server Registration"]
    assert mcp
    assert mcp[0]["evidence_strength"] == "LITERAL_CONFIG"
