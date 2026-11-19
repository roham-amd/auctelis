"""AUTHORITY.lock write / check / diff (north-star direction 1 MVP)."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import (
    build_authority_lock,
    check_locked,
    classify_record_change,
    diff_authority_locks,
    identity_key,
    write_authority_lock,
)
from auctelis.cli import main
from auctelis.lock_io import load_authority_lock


def _repo_with_mcp(root: Path, servers: dict) -> None:
    path = root / ".cursor" / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n", encoding="utf-8")


def test_lock_write_check_and_diff(tmp_path: Path):
    root = tmp_path / "repo"
    _repo_with_mcp(
        root,
        {
            "echo": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-everything@1.0.0"],
            }
        },
    )
    dest, lock = write_authority_lock(root, accept_gated=True)
    assert dest.name == "AUTHORITY.lock"
    assert lock["version"] == 1
    assert lock["records"]
    assert any(r["name"] == "echo" for r in lock["records"])
    assert all(r.get("identity_key") for r in lock["records"])

    report, code = check_locked(root)
    assert code == 0
    assert report["verdict"] == "LOCKED"

    _repo_with_mcp(
        root,
        {
            "echo": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-everything@1.0.0"],
            },
            "newcomer": {"command": "npx", "args": ["-y", "evil-pkg"]},
        },
    )
    report2, code2 = check_locked(root)
    assert code2 == 1
    assert report2["verdict"] == "NEEDS_REVIEW"
    assert any("addition" in line for line in report2["lines"])

    head = build_authority_lock(root)
    delta = diff_authority_locks(lock, head)
    assert delta["summary"]["records_added"] >= 1
    assert delta["summary"]["additions"] >= 1
    assert delta["summary"]["meaningful_authority_change"] is True
    assert delta["summary"]["authority_changed"] is True


def test_identity_key_path_independent():
    a = {
        "host": "cursor",
        "kind": "MCP Server Registration",
        "name": "echo",
        "path": "a/mcp.json",
    }
    b = {
        "host": "cursor",
        "kind": "MCP Server Registration",
        "name": "echo",
        "path": "b/mcp.json",
    }
    assert identity_key(a) == identity_key(b)


def test_classify_representation_vs_expansion():
    before = {
        "capabilities": ["execute_commands"],
        "destinations": [],
        "env_keys": [],
        "pin_state": "pinned",
        "approval_posture": "prompt",
        "path": "old/mcp.json",
        "digest": "aaa",
        "fingerprint": "fp1",
        "script_digest": "s1",
    }
    moved = {**before, "path": "new/mcp.json", "digest": "bbb", "fingerprint": "fp2"}
    assert classify_record_change(before, moved) == "representation"

    body_only = {**before, "script_digest": "s2"}
    assert classify_record_change(before, body_only) == "representation"

    broader = {**before, "pin_state": "floating", "env_keys": ["API_KEY"]}
    assert classify_record_change(before, broader) == "expansion"

    narrower = {**before, "capabilities": []}
    assert classify_record_change(before, narrower) == "reduction"


def test_path_move_is_representation_not_add_remove():
    base = {
        "version": 2,
        "records": [
            {
                "id": "cursor/MCP Server Registration/echo@old/mcp.json",
                "identity_key": "cursor|mcp server registration|echo",
                "host": "cursor",
                "kind": "MCP Server Registration",
                "name": "echo",
                "path": "old/mcp.json",
                "digest": "aaa",
                "fingerprint": "fp1",
                "pin_state": "pinned",
                "approval_posture": "prompt",
                "capabilities": ["execute_commands"],
                "destinations": [],
                "env_keys": [],
            }
        ],
    }
    head = {
        "version": 2,
        "records": [
            {
                "id": "cursor/MCP Server Registration/echo@new/mcp.json",
                "identity_key": "cursor|mcp server registration|echo",
                "host": "cursor",
                "kind": "MCP Server Registration",
                "name": "echo",
                "path": "new/mcp.json",
                "digest": "bbb",
                "fingerprint": "fp2",
                "pin_state": "pinned",
                "approval_posture": "prompt",
                "capabilities": ["execute_commands"],
                "destinations": [],
                "env_keys": [],
            }
        ],
    }
    delta = diff_authority_locks(base, head)
    assert delta["summary"]["records_added"] == 0
    assert delta["summary"]["records_removed"] == 0
    assert delta["summary"]["records_changed"] == 1
    assert delta["changes"]["changed"][0]["change_class"] == "representation"
    assert delta["summary"]["meaningful_authority_change"] is False
    assert delta["summary"]["authority_changed"] is True


def test_load_authority_lock_roundtrip(tmp_path: Path):
    root = tmp_path / "repo"
    _repo_with_mcp(root, {"x": {"command": "node", "args": ["x.js"]}})
    dest, lock = write_authority_lock(root)
    loaded = load_authority_lock(dest)
    assert loaded["version"] == lock["version"]
    assert loaded["lock_hash"] == lock["lock_hash"]
    assert len(loaded["records"]) == len(lock["records"])


def test_build_authority_lock_reuses_scan(tmp_path: Path, monkeypatch):
    """``scan --locked`` must not pay for a second full security scan."""
    from auctelis.security import engine as engine_mod

    root = tmp_path / "repo"
    _repo_with_mcp(root, {"x": {"command": "node", "args": ["x.js"]}})
    calls = {"n": 0}
    real = engine_mod.run_authority_inventory

    def counted(path, **kwargs):
        calls["n"] += 1
        return real(path, **kwargs)

    monkeypatch.setattr(engine_mod, "run_authority_inventory", counted)
    # Import after patch so authority_lock sees the same module attribute.
    from auctelis import authority_lock as lock_mod

    monkeypatch.setattr(lock_mod, "run_authority_inventory", counted)
    scan = lock_mod.run_authority_inventory(root)
    assert calls["n"] == 1
    lock_a = lock_mod.build_authority_lock(root, scan=scan)
    lock_b = lock_mod.build_authority_lock(root, scan=scan)
    assert calls["n"] == 1
    assert lock_a["lock_hash"] == lock_b["lock_hash"]
    lock_mod.build_authority_lock(root)
    assert calls["n"] == 2


def test_lock_cli_roundtrip(tmp_path: Path):
    root = tmp_path / "repo"
    _repo_with_mcp(root, {"x": {"command": "node", "args": ["x.js"]}})
    assert main(["lock", str(root)]) == 0
    assert (root / "AUTHORITY.lock").is_file()
    assert main(["lock", str(root), "--check"]) == 0
    assert main(["check", str(root)]) == 0
    from auctelis.cli import main_dev

    assert (
        main_dev(
            [
                "scan",
                str(root),
                "--locked",
                "-o",
                str(tmp_path / "out"),
                "--fail-on",
                "never",
            ]
        )
        == 0
    )

    _repo_with_mcp(
        root,
        {
            "x": {"command": "node", "args": ["x.js"]},
            "y": {"command": "node", "args": ["y.js"]},
        },
    )
    assert main(["lock", str(root), "--check"]) == 1
    assert main(["check", str(root)]) == 1
    assert (
        main_dev(
            [
                "scan",
                str(root),
                "--locked",
                "-o",
                str(tmp_path / "out2"),
                "--fail-on",
                "never",
            ]
        )
        == 1
    )


def test_write_omits_approvals_legacy_locks_still_load(tmp_path: Path):
    """AUCT-009: new locks omit approvals; v1 locks that still have them load fine."""
    root = tmp_path / "repo"
    _repo_with_mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    dest, lock = write_authority_lock(root)
    assert "approvals" not in lock
    assert "approved_findings" not in lock

    legacy = dict(lock)
    legacy["approvals"] = []
    legacy["approved_findings"] = []
    path = tmp_path / "legacy.lock"
    path.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")
    loaded = load_authority_lock(path)
    assert loaded.get("approvals") == []
    assert loaded.get("approved_findings") == []
    head = build_authority_lock(root)
    delta = diff_authority_locks(loaded, head)
    assert delta["summary"]["authority_changed"] in {True, False}
    assert dest.is_file()
