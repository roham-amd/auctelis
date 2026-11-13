"""Authority Watch / 0.3.4 plan: wheel-safe imports, hooks, strict default."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.cli import main
from auctelis.export.pr_comment import escape_markdown, render_authority_diff_comment
from auctelis.gate import run_gate
from auctelis.hooks import install_hooks


def test_product_dispatch_imports_without_packaging(monkeypatch):
    """Importing the product CLI must not require packaging at module load."""
    # Simulate a clean wheel: packaging may exist in the test env; assert the
    # product dispatch module does not import auctelis.deps / build at load.
    import importlib
    import sys

    mod = importlib.import_module("auctelis.cli.dispatch")
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "from auctelis.build import" not in src.split("def ")[0]
    assert "from auctelis.deps import" not in src.split("def ")[0]
    assert "auctelis.cli.dispatch" in sys.modules


def test_hook_install_writes_session_and_pretool(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    hooks_dir = home / ".auctelis" / "hooks"
    result = install_hooks(home=home, hooks_dir=hooks_dir, wire_claude=True)
    assert (hooks_dir / "auctelis-session-delta.py").is_file()
    assert (hooks_dir / "claude_pretool_authority_hook.py").is_file()
    settings = home / ".claude" / "settings.json"
    assert settings.is_file()
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert "SessionStart" in data.get("hooks", {})
    assert "PreToolUse" in data.get("hooks", {})
    assert result["session_hook"]


def test_hook_cli_install(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    code = main(
        [
            "hook",
            "install",
            "--home",
            str(home),
            "--hooks-dir",
            str(home / "hooks"),
            "--no-wire",
            "--session-only",
        ]
    )
    assert code == 0
    assert (home / "hooks" / "auctelis-session-delta.py").is_file()


def test_escape_markdown_keeps_path_dots():
    text = escape_markdown(".cursor/mcp.json")
    assert r"\." not in text
    assert ".cursor/mcp.json" in text


def test_pr_comment_tags_evidence_strength_and_skips_coverage_pct():
    comment = render_authority_diff_comment(
        {
            "findings": [],
            "coverage": {
                "not_verified": ["runtime"],
                "deterministically_discovered": 1,
                "component_counts_by_maturity": {"SUPPORTED": 1},
            },
        },
        risk_delta={
            "summary": {"gated_findings_added": 1},
            "changes": {
                "gated_new_findings": [
                    {
                        "finding_id": "F-001",
                        "severity": "HIGH",
                        "title": "Remote MCP",
                        "impact": "network + secrets",
                        "evidence_strength": "LITERAL_CONFIG",
                        "finding_class": "SECURITY_FINDING",
                        "confidence": "LITERAL_CONFIG",
                        "evidence_ids": ["E-001"],
                    }
                ]
            },
        },
    )
    assert "LITERAL_CONFIG" in comment
    assert "coverage %" not in comment.lower()
    assert "auctelis explain" in comment


def test_gate_strict_ruleset_default_on(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}),
        encoding="utf-8",
    )
    (root / "CODEOWNERS").write_text("* @sec\nAUTHORITY.lock @sec\n", encoding="utf-8")
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "a": {"command": "node", "args": ["a.js"]},
                    "b": {"command": "node", "args": ["b.js"]},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    report, code = run_gate(root, base_lock=base)
    assert report["strict_ruleset"] is True
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"

    soft_code = main(["gate", str(root), "--base-lock", str(base), "--no-strict-ruleset"])
    assert soft_code == 0


def test_hook_cli_pretool_only_and_idempotent(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    hooks = home / "hooks"
    assert (
        main(
            [
                "hook",
                "install",
                "--home",
                str(home),
                "--hooks-dir",
                str(hooks),
                "--pretool-only",
                "--no-wire",
            ]
        )
        == 0
    )
    assert (hooks / "claude_pretool_authority_hook.py").is_file()
    assert not (hooks / "auctelis-session-delta.py").is_file()
    # Idempotent reinstall with wire
    assert (
        main(
            [
                "hook",
                "install",
                "--home",
                str(home),
                "--hooks-dir",
                str(hooks),
            ]
        )
        == 0
    )
    settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len(settings["hooks"]["SessionStart"]) == 1
    assert len(settings["hooks"]["PreToolUse"]) == 1


def test_lock_diff_dedupes_url_and_host_destination():
    from auctelis.authority_lock import render_lock_diff_lines

    lines = render_lock_diff_lines(
        added=[
            {
                "kind": "MCP Server Registration",
                "name": "remote",
                "path": ".cursor/mcp.json",
                "destinations": [
                    "http://mcp.example.invalid/sse",
                    "mcp.example.invalid",
                ],
                "capabilities": ["network"],
                "pin_state": "floating",
                "env_keys": [],
            }
        ],
        removed=[],
        changed=[],
    )
    assert len(lines) == 1
    # Host appears once (URL normalized), not twice.
    assert lines[0].count("mcp.example.invalid") == 1


def test_ci_init_writes_lockless_workflow(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}),
        encoding="utf-8",
    )
    code = main(["ci", "init", "--owner", "@sec", "--force", str(root)])
    assert code == 0
    wf = (root / ".github" / "workflows" / "auctelis-gate.yml").read_text(encoding="utf-8")
    assert 'locked: "false"' in wf
    assert 'strict-ruleset: "true"' in wf
    out = capsys.readouterr().out
    assert "locked: false" in out


def test_product_cli_rejects_dev_only_snapshot():
    # Product entry must not expose kill-list execute commands as first-class.
    from auctelis.cli.parser import build_parser

    parser = build_parser(include_dev=False)
    help_text = parser.format_help()
    assert "snapshot" not in help_text
    assert "artifact-vet" not in help_text
    assert "hook" in help_text


def test_pretool_hook_refuses_unknown_mcp(tmp_path: Path, monkeypatch, capsys):
    import importlib.util

    hook_path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "auctelis"
        / "templates"
        / "claude_pretool_authority_hook.py"
    )
    spec = importlib.util.spec_from_file_location("pretool_hook", hook_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    root = tmp_path / "repo"
    root.mkdir()
    lock = {
        "version": 1,
        "records": [
            {
                "kind": "MCP Server Registration",
                "name": "allowed",
                "id": "allowed",
            }
        ],
        "mcp_tools": {},
    }
    (root / "AUTHORITY.lock").write_text(json.dumps(lock), encoding="utf-8")
    monkeypatch.chdir(root)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    payload = json.dumps({"tool_name": "mcp__evil__tool", "tool_input": {"server": "evil"}})
    monkeypatch.setenv("CLAUDE_TOOL_INPUT", payload)
    assert mod.main() == 2
    # Empty allowlist also fail-closed for MCP-shaped tools
    (root / "AUTHORITY.lock").write_text(
        json.dumps({"version": 1, "records": [], "mcp_tools": {}}), encoding="utf-8"
    )
    assert mod.main() == 2
