"""Fail-closed lock/gate behavior and mcp_tools diff coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from auctelis.authority_lock import (
    delta_label,
    diff_authority_locks,
    write_authority_lock,
)
from auctelis.cli import main
from auctelis.gate import run_gate
from auctelis.lock_io import AuthorityLockError, load_authority_lock
from auctelis.watch import build_watch_report

_EMPTY = {"version": 1, "records": [], "policy_hash": None, "mcp_tools": {}}


def _mcp(root: Path, name: str = "a") -> None:
    cursor = root / ".cursor"
    cursor.mkdir(parents=True, exist_ok=True)
    (cursor / "mcp.json").write_text(
        json.dumps({"mcpServers": {name: {"command": "node", "args": [f"{name}.js"]}}}),
        encoding="utf-8",
    )


def _sealed_repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    _mcp(root)
    (root / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text(
        (root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return root, base


def test_gate_unparsed_head_is_needs_review(tmp_path: Path):
    root, base = _sealed_repo(tmp_path)
    (root / ".cursor" / "mcp.json").write_text('{"mcpServers": {', encoding="utf-8")
    report, code = run_gate(root, base_lock=base, check_ruleset=False)
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert "could not be parsed" in str(report.get("error") or "")


def test_gate_unparsed_head_fails_even_with_trusted_head_lock(tmp_path: Path):
    root, base = _sealed_repo(tmp_path)
    (root / ".cursor" / "mcp.json").write_text('{"mcpServers": {', encoding="utf-8")
    report, code = run_gate(root, base_lock=base, head_lock=base, check_ruleset=False)
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"


def test_gate_missing_base_lock_fails_closed(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    report, code = run_gate(
        root, base_lock=tmp_path / "missing.lock", check_ruleset=False
    )
    assert code == 2
    assert report["verdict"] == "FAIL_CLOSED"
    assert "cannot read base lock" in report["error"]


def test_gate_missing_head_lock_path_fails_closed(tmp_path: Path):
    root, base = _sealed_repo(tmp_path)
    report, code = run_gate(
        root,
        base_lock=base,
        head_lock=tmp_path / "missing-head.lock",
        check_ruleset=False,
    )
    assert code == 2
    assert report["verdict"] == "FAIL_CLOSED"
    assert "head lock not found" in report["error"]


@pytest.mark.parametrize(
    "body",
    [
        '{"version": 1, "records": [',
        "",
        "[]",
        "not a lock at all",
    ],
)
def test_corrupt_lock_fails_closed(tmp_path: Path, body: str):
    path = tmp_path / "AUTHORITY.lock"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(AuthorityLockError):
        load_authority_lock(path)


def test_legacy_yaml_mcp_tools_lock_still_loads(tmp_path: Path):
    path = tmp_path / "AUTHORITY.lock"
    path.write_text("mcp_tools:\n  read: sha256:abc\n", encoding="utf-8")
    lock = load_authority_lock(path)
    assert lock["mcp_tools"]["read"] == "sha256:abc"


def test_watch_reports_unusable_lock(tmp_path: Path, capsys):
    home = tmp_path / "home"
    (home / ".auctelis").mkdir(parents=True)
    _mcp(home)
    (home / ".auctelis" / "AUTHORITY.lock").write_text(
        '{"records": [', encoding="utf-8"
    )
    report, _cards, _scan = build_watch_report(home=home)
    assert report["error"]
    assert main(["watch", "--home", str(home), "--delta-only"]) == 2
    out = capsys.readouterr().out
    assert out.startswith("auctelis:")


def test_mcp_tools_diff_is_meaningful():
    base = {**_EMPTY, "mcp_tools": {"read": "sha256:a"}}
    head = {**_EMPTY, "mcp_tools": {"read": "sha256:a", "write": "sha256:b"}}
    delta = diff_authority_locks(base, head)
    summary = delta["summary"]
    assert summary["meaningful_authority_change"] is True
    assert summary["mcp_tools_added"] == 1
    assert delta["changes"]["mcp_tools_added"] == ["write"]
    assert any("mcp tool pin" in line for line in delta["lines"])
    assert delta_label(summary) == "GROWTH"

    removed = diff_authority_locks(head, base)
    assert removed["summary"]["mcp_tools_removed"] == 1
    assert delta_label(removed["summary"]) == "REDUCTION"


def test_lock_file_uses_lf_newlines(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root)
    dest, _lock = write_authority_lock(root)
    assert b"\r\n" not in dest.read_bytes()


def test_gate_policy_change_is_growth(tmp_path: Path):
    root, base = _sealed_repo(tmp_path)
    (root / ".auctelis.yml").write_text(
        "version: 1\npolicy:\n  mode: advisory\n  fail_on: never\n",
        encoding="utf-8",
    )
    report, _code = run_gate(root, base_lock=base, check_ruleset=False)
    assert report["label"] == "GROWTH"
    assert report["delta"]["summary"]["policy_changed"] is True


def test_watch_changed_card_shows_old_to_new(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(home, "linear")
    assert main(["watch", "--home", str(home), "--seal"]) == 0
    capsys.readouterr()
    (home / ".cursor" / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "linear": {
                        "command": "node",
                        "args": ["linear.js"],
                        "env": {"LINEAR_TOKEN": "${LINEAR_TOKEN}"},
                        "url": "https://mcp.linear.app/sse",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    assert main(["watch", "--home", str(home), "--delta-only"]) == 1
    out = capsys.readouterr().out
    assert out.startswith('~ mcp "linear"')
    assert "host:" in out or "launcher:" in out
    assert "env: +LINEAR_TOKEN" in out


def test_watch_removal_after_surface_deleted(tmp_path: Path, capsys):
    home = tmp_path / "home"
    _mcp(home)
    assert main(["watch", "--home", str(home), "--seal"]) == 0
    capsys.readouterr()
    (home / ".cursor" / "mcp.json").unlink()
    assert main(["watch", "--home", str(home), "--delta-only"]) == 1
    out = capsys.readouterr().out
    assert "removed" in out
