"""Authority Watch + Cursor/Claude hook contract (the 90-day first screen)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from auctelis.cli import main
from auctelis.cli.parser import build_parser, normalize_argv
from auctelis.export.pr_comment import render_authority_diff_comment

_ROOT = Path(__file__).resolve().parents[1]


def _mcp(home: Path, servers: dict) -> None:
    cursor = home / ".cursor"
    cursor.mkdir(parents=True, exist_ok=True)
    (cursor / "mcp.json").write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def test_bare_auctelis_is_watch_not_scan(tmp_path: Path):
    assert normalize_argv([], cwd=tmp_path) == ["watch"]
    assert "watch" in build_parser().format_help()
    listed = [
        line.strip()
        for line in build_parser().format_help().splitlines()
        if line.startswith("    ")
    ]
    assert any(line.startswith("watch") for line in listed)
    assert not any(line.startswith("scan") for line in listed)
    assert not any(line.startswith("vet") for line in listed)


def test_watch_first_run_shows_reach_and_cards(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(
        home,
        {
            "linear": {
                "url": "https://mcp.linear.app/sse",
                "env": {"LINEAR_TOKEN": "${LINEAR_TOKEN}"},
            }
        },
    )
    code = main(["watch", "--home", str(home)])
    out = capsys.readouterr().out
    assert code == 1
    assert "Reach: 1 MCP, 0 hooks" in out
    assert '+ mcp "linear" → mcp.linear.app · network' in out
    assert "publisher NOT VERIFIED" in out
    assert "AUCTELIS-RULE" not in out


def test_watch_empty_home_is_an_explicit_zero_baseline(tmp_path: Path, capsys):
    home = tmp_path / "empty"
    home.mkdir()
    code = main(["watch", "--home", str(home)])
    out = capsys.readouterr().out
    assert code == 0
    assert "0 MCP, 0 hooks, 0 skills, 0 CI" in out
    assert "No host config found" in out


def test_watch_seal_then_quiet_delta(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(home, {"linear": {"url": "https://mcp.linear.app/sse"}})
    assert main(["watch", "--home", str(home), "--seal"]) == 0
    capsys.readouterr()
    lock = home / ".auctelis" / "AUTHORITY.lock"
    assert lock.is_file()
    assert json.loads(lock.read_text(encoding="utf-8"))["records"]

    assert main(["watch", "--home", str(home)]) == 0
    quiet = capsys.readouterr().out
    assert "No authority change since you sealed." in quiet

    assert main(["watch", "--home", str(home), "--delta-only"]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_watch_delta_only_prints_one_addition_line(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(home, {"linear": {"url": "https://mcp.linear.app/sse"}})
    assert main(["watch", "--home", str(home), "--seal"]) == 0
    capsys.readouterr()
    _mcp(
        home,
        {
            "linear": {"url": "https://mcp.linear.app/sse"},
            "github": {"command": "npx", "args": ["-y", "server-github"]},
        },
    )
    assert main(["watch", "--home", str(home), "--delta-only"]) == 1
    lines = [line for line in capsys.readouterr().out.strip().splitlines() if line]
    assert len(lines) == 1
    assert lines[0].startswith('+ mcp "github"')
    assert "publisher NOT VERIFIED" in lines[0]


def test_watch_delta_only_is_silent_before_seal(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(home, {"linear": {"url": "https://mcp.linear.app/sse"}})
    # The session hook must not narrate the unsealed baseline every session.
    assert main(["watch", "--home", str(home), "--delta-only"]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_watch_reports_removal_after_config_deleted(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(
        home,
        {
            "linear": {"url": "https://mcp.linear.app/sse"},
            "github": {"command": "node", "args": ["g.js"]},
        },
    )
    assert main(["watch", "--home", str(home), "--seal"]) == 0
    capsys.readouterr()
    _mcp(home, {"linear": {"url": "https://mcp.linear.app/sse"}})
    assert main(["watch", "--home", str(home), "--delta-only"]) == 1
    out = capsys.readouterr().out
    assert '- mcp "github" · removed' in out


def test_watch_refuses_agent_seal(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AUCTELIS_AGENT", "1")
    assert main(["watch", "--home", str(home), "--seal"]) == 2
    assert not (home / ".auctelis" / "AUTHORITY.lock").exists()


def test_hook_install_wires_cursor_and_broad_claude_matcher(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    assert main(["hook", "install", "--home", str(home)]) == 0
    claude = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    pretool = claude["hooks"]["PreToolUse"][0]
    assert pretool["matcher"] == ".*"
    cursor = json.loads((home / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    assert "sessionStart" in cursor["hooks"]
    assert "beforeMCPExecution" in cursor["hooks"]
    assert (home / ".auctelis" / "hooks" / "auctelis_cursor_hook.py").is_file()


def test_hook_status_reports_not_wired_then_firing(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    assert main(["hook", "status", "--home", str(home)]) == 0
    out = capsys.readouterr().out
    assert "not_wired" in out

    assert main(["hook", "install", "--home", str(home)]) == 0
    (home / ".auctelis").mkdir(exist_ok=True)
    (home / ".auctelis" / "AUTHORITY.lock").write_text(
        json.dumps({"version": 1, "records": []}), encoding="utf-8"
    )
    import auctelis.hooks as hooks_mod

    monkeypatch.setattr(hooks_mod.shutil, "which", lambda _cmd: "/usr/bin/auctelis")
    assert main(["hook", "status", "--home", str(home)]) == 0
    out = capsys.readouterr().out
    assert "Claude Code: firing" in out
    assert "Cursor: firing" in out


def _load_template(name: str):
    path = _ROOT / "tools" / "auctelis" / "templates" / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cursor_hook_allows_known_and_denies_unknown_mcp(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "AUTHORITY.lock").write_text(
        json.dumps(
            {
                "version": 1,
                "records": [
                    {
                        "kind": "MCP Server Registration",
                        "name": "linear",
                        "id": "linear",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    script = _ROOT / "tools" / "auctelis" / "templates" / "auctelis_cursor_hook.py"

    def run(payload: dict) -> dict:
        env = {"CURSOR_PROJECT_DIR": str(project), "PATH": ""}
        proc = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={**env, "SYSTEMROOT": "C:\\Windows"} if sys.platform == "win32" else env,
            check=False,
        )
        return json.loads(proc.stdout)

    allowed = run({"hook_event_name": "beforeMCPExecution", "tool_name": "mcp__linear__read"})
    assert allowed["permission"] == "allow"
    denied = run({"hook_event_name": "beforeMCPExecution", "tool_name": "mcp__evil__run"})
    assert denied["permission"] == "deny"
    edit = run({"hook_event_name": "beforeFileEdit", "file_path": ".cursor/mcp.json"})
    assert edit["permission"] == "deny"


def test_claude_hook_default_deny_and_known_mcp(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "AUTHORITY.lock").write_text(
        json.dumps(
            {
                "version": 1,
                "records": [
                    {
                        "kind": "MCP Server Registration",
                        "name": "linear",
                        "id": "linear",
                    }
                ],
                "mcp_tools": {},
            }
        ),
        encoding="utf-8",
    )
    mod = _load_template("claude_pretool_authority_hook.py")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv(
        "CLAUDE_TOOL_INPUT",
        json.dumps({"tool_name": "mcp__linear__read", "tool_input": {}}),
    )
    assert mod.main() == 0
    monkeypatch.setenv(
        "CLAUDE_TOOL_INPUT",
        json.dumps({"tool_name": "mcp__evil__run", "tool_input": {}}),
    )
    assert mod.main() == 2


def test_pr_comment_marks_not_parsed_and_has_one_verdict():
    comment = render_authority_diff_comment(
        {
            "findings": [],
            "coverage": {
                "unparsed_agent_config_count": 1,
                "not_verified": ["runtime"],
            },
        }
    )
    assert "**Verdict:**" in comment
    assert "NEEDS_REVIEW" in comment
    assert "NOT PARSED" in comment
    assert "NOT PARSED: 1 agent config" in comment
    assert "label `NONE`" in comment


def test_gate_verdict_wins_in_pr_comment(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    (root / ".cursor").mkdir(parents=True)
    (root / "CODEOWNERS").write_text("* @sec\nAUTHORITY.lock @sec\n", encoding="utf-8")
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}),
        encoding="utf-8",
    )
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
    out = tmp_path / "out"
    out.mkdir()
    (out / "findings.json").write_text(json.dumps({"findings": []}), encoding="utf-8")
    monkeypatch.setenv("AUCTELIS_OUTPUT_DIR", str(out))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert main(["gate", str(root), "--base-lock", str(base), "--strict-ruleset"]) == 1
    comment = (out / "pr-comment.md").read_text(encoding="utf-8")
    assert "**Verdict:** `NEEDS_REVIEW`" in comment
    assert "label `GROWTH`" in comment


def test_release_manifest_is_lockless_first():
    manifest = json.loads(
        (_ROOT / "canonical" / "release-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["primary_command"] == "auctelis watch"
    assert manifest["interfaces"]["locked_action_default"] is False
    assert manifest["interfaces"]["cursor_hooks"] is True
