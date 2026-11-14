"""North-star 30-day deliverables: first-run, why, heartbeat, tripwire help."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.cli import main
from auctelis.cli.parser import CORE_PUBLIC_COMMANDS, PUBLIC_PATH, build_parser
from auctelis.ledger import load_heartbeat, load_ledger, record_heartbeat
from auctelis.watch import build_watch_report, render_watch


def _mcp(home: Path, servers: dict) -> None:
    cursor = home / ".cursor"
    cursor.mkdir(parents=True, exist_ok=True)
    (cursor / "mcp.json").write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def test_public_path_is_lockfile_not_gate():
    assert "why" in PUBLIC_PATH
    assert "gate" not in PUBLIC_PATH
    assert "ci" not in CORE_PUBLIC_COMMANDS
    assert "gate" not in CORE_PUBLIC_COMMANDS
    help_text = build_parser().format_help()
    assert "tripwire" in help_text.lower()


def test_first_run_highlights_not_growth_exit(tmp_path: Path, capsys):
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
    report, cards, _scan = build_watch_report(home=home)
    assert report["first_run"] is True
    assert report["meaningful"] is False
    assert report["schema_version"] == "watch-report/1"
    assert any("linear" in c for c in cards)
    text = render_watch(report, cards)
    assert "New reach" in text or "Inventory:" in text
    assert "every current record appears as new" not in text
    assert main(["watch", "--home", str(home)]) == 0
    assert "Inventory:" in capsys.readouterr().out


def test_why_prints_path(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(home, {"linear": {"url": "https://mcp.linear.app/sse"}})
    assert main(["why", "linear", "--home", str(home)]) == 0
    out = capsys.readouterr().out
    assert 'mcp "linear"' in out
    assert "path:" in out
    assert "mcp.linear.app" in out
    assert main(["why", "does-not-exist", "--home", str(home)]) == 1


def test_watch_json_first_run_then_sealed(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(home, {"linear": {"url": "https://mcp.linear.app/sse"}})
    assert main(["watch", "--home", str(home), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == "watch-report/1"
    assert report["first_run"] is True
    assert report["meaningful"] is False
    assert main(["watch", "--home", str(home), "--seal"]) == 0
    capsys.readouterr()
    assert main(["watch", "--home", str(home), "--json"]) == 0
    sealed = json.loads(capsys.readouterr().out)
    assert sealed.get("first_run") is False
    assert sealed["lock_present"] is True


def test_hook_status_shows_recent_deltas(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    assert main(["hook", "install", "--home", str(home)]) == 0
    (home / ".auctelis" / "AUTHORITY.lock").write_text(
        json.dumps({"version": 1, "records": []}), encoding="utf-8"
    )
    import auctelis.hooks as hooks_mod

    monkeypatch.setattr(hooks_mod.shutil, "which", lambda _cmd: "/usr/bin/auctelis")
    record_heartbeat(
        home=home,
        had_delta=True,
        delta_lines=['+ mcp "stripe" → mcp.stripe.com'],
    )
    assert main(["hook", "status", "--home", str(home)]) == 0
    out = capsys.readouterr().out
    assert "Recent deltas:" in out
    assert "mcp.stripe.com" in out
    assert "firing (last:" in out


def test_heartbeat_and_ledger_roundtrip(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    record_heartbeat(
        home=home,
        host="session",
        event="sessionStart",
        had_delta=True,
        delta_lines=['+ mcp "x" → example.com'],
    )
    hb = load_heartbeat(home=home)
    assert hb is not None
    assert hb["had_delta"] is True
    assert hb["last_fired"]
    ledger = load_ledger(home=home)
    assert len(ledger) == 1
    assert "example.com" in ledger[0]["lines"][0]


def test_session_hook_writes_heartbeat(tmp_path: Path, monkeypatch):
    """Installed session hook must leave a heartbeat after a quiet watch."""
    import os
    import subprocess
    import sys

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(home))

    # Seal empty baseline so watch --delta-only is quiet (exit 0).
    (home / ".auctelis").mkdir(parents=True)
    (home / ".auctelis" / "AUTHORITY.lock").write_text(
        json.dumps({"version": 1, "records": [], "mcp_tools": {}}),
        encoding="utf-8",
    )

    root = Path(__file__).resolve().parents[1]
    script = root / "tools" / "auctelis" / "templates" / "auctelis-session-delta.py"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if sys.platform == "win32":
        wrapper = bin_dir / "auctelis.cmd"
        wrapper.write_text(
            f'@echo off\r\n"{sys.executable}" -m auctelis %*\r\n',
            encoding="utf-8",
        )
    else:
        wrapper = bin_dir / "auctelis"
        wrapper.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" -m auctelis "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)

    env = {
        **os.environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "PYTHONPATH": str(root / "tools"),
        "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
    }
    proc = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(home),
    )
    assert proc.returncode == 0
    hb = load_heartbeat(home=home)
    assert hb is not None
    assert hb.get("last_fired")
