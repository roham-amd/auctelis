"""Days 4-14: pinned facts + hostile lock load/diff."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import (
    args_digest,
    build_authority_lock,
    diff_authority_locks,
    write_authority_lock,
)
from auctelis.cli import main
from auctelis.gate import run_gate
from auctelis.lock_io import AuthorityLockError, load_authority_lock, validate_authority_lock


def _mcp(root: Path, servers: dict) -> None:
    path = root / ".cursor" / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def test_lock_records_launcher_args_digest_and_url_host(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(
        root,
        {
            "svc": {
                "command": "npx",
                "args": ["-y", "@scope/pkg@1.2.3"],
                "url": "https://api.example.com/mcp",
                "env": {"API_KEY": "x"},
            }
        },
    )
    lock = build_authority_lock(root)
    rec = next(r for r in lock["records"] if r["name"] == "svc")
    assert rec["launcher"] == "npx"
    assert rec["args_digest"] == args_digest(["-y", "@scope/pkg@1.2.3"])
    assert rec["url_host"] == "api.example.com"
    assert "api.example.com" in rec["destinations"]
    server = lock["mcp_servers"]["svc"]
    assert server["command"] == "npx"
    assert server["args_digest"] == rec["args_digest"]


def test_same_name_package_swap_is_replacement(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"svc": {"command": "npx", "args": ["pkg@1.0.0"]}})
    _, base = write_authority_lock(root, accept_gated=True)
    _mcp(root, {"svc": {"command": "npx", "args": ["pkg@2.0.0"]}})
    head = build_authority_lock(root)
    delta = diff_authority_locks(base, head)
    assert delta["summary"]["replacements"] >= 1 or delta["summary"]["expansions"] >= 1
    assert delta["summary"]["meaningful_authority_change"] is True


def test_schema_rejects_malformed_lock(tmp_path: Path):
    bad = tmp_path / "bad.lock"
    bad.write_text(json.dumps({"version": 1, "records": "nope"}), encoding="utf-8")
    try:
        load_authority_lock(bad)
        raise AssertionError("expected AuthorityLockError")
    except AuthorityLockError:
        pass


def test_hollow_base_fails_closed(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    (root / ".github").mkdir(parents=True)
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    hollow = tmp_path / "hollow.lock"
    hollow.write_text(
        json.dumps({"version": 1, "records": [], "lock_hash": "deadbeef", "mcp_tools": {}}),
        encoding="utf-8",
    )
    report, code = run_gate(root, base_lock=hollow)
    assert code == 1
    assert report["verdict"] == "FAIL_CLOSED"


def test_reordered_records_not_meaningful(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    lock = build_authority_lock(root)
    reordered = dict(lock)
    reordered["records"] = list(reversed(list(lock["records"])))
    validate_authority_lock(reordered)
    delta = diff_authority_locks(lock, reordered)
    assert delta["summary"]["meaningful_authority_change"] is False


def test_lock_snapshot_merges_mcp_tools(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    snap = tmp_path / "tools.json"
    snap.write_text(
        json.dumps(
            {
                "tools": [
                    {"name": "read", "description": "Read a file"},
                    {"name": "write", "description": "Write a file"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert main(["lock", str(root), "--snapshot", str(snap), "--accept-gated"]) == 0
    sealed = json.loads((root / "AUTHORITY.lock").read_text(encoding="utf-8"))
    assert "read" in sealed["mcp_tools"]
    assert sealed["mcp_tools"]["read"].startswith("sha256:")
