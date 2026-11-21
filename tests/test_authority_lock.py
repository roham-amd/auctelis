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


def test_auct030_pin_swap_never_reduction():
    """AUCT-030: package/launcher swaps are never silent REDUCTION."""
    from auctelis.authority_lock import args_digest, delta_label, package_stem_from_args
    from auctelis.reach_tiers import TIER_FAIL, delta_max_reach_tier

    floating = {
        "kind": "MCP Server Registration",
        "name": "demo",
        "path": ".cursor/mcp.json",
        "launcher": "npx",
        "args_digest": args_digest(["-y", "@linear/mcp"]),
        "package_stem": package_stem_from_args("npx", ["-y", "@linear/mcp"]),
        "url_host": "",
        "pin_state": "floating",
        "capabilities": ["invoke_tools"],
        "destinations": [],
        "env_keys": ["API_KEY"],
        "permission_allows": [],
        "approval_posture": "prompt",
        "evidence_strength": "LITERAL_CONFIG",
    }
    # Package swap + floating→pinned must not PASS as REDUCTION.
    swapped = {
        **floating,
        "args_digest": args_digest(["-y", "@evil/pwn@1.0.0"]),
        "package_stem": package_stem_from_args("npx", ["-y", "@evil/pwn@1.0.0"]),
        "pin_state": "pinned",
    }
    assert classify_record_change(floating, swapped) in {"replacement", "mixed"}

    # Launcher hijack npx → sh.
    hijack = {**floating, "launcher": "sh", "pin_state": "unknown"}
    assert classify_record_change(floating, hijack) in {"replacement", "mixed"}

    # Args swap + env shrink → mixed GROWTH.
    env_drop = {
        **swapped,
        "env_keys": [],
    }
    assert classify_record_change(floating, env_drop) == "mixed"

    # Same-package pin tightening stays REDUCTION.
    pinned = {
        **floating,
        "args_digest": args_digest(["-y", "@linear/mcp@1.2.3"]),
        "package_stem": package_stem_from_args("npx", ["-y", "@linear/mcp@1.2.3"]),
        "pin_state": "pinned",
    }
    assert floating["package_stem"] == pinned["package_stem"] == "@linear/mcp"
    assert classify_record_change(floating, pinned) == "reduction"

    # End-to-end delta: swap is GROWTH / NEEDS_REVIEW tier.
    def _lock(rec: dict) -> dict:
        return {
            "version": 1,
            "records": [
                {
                    **rec,
                    "id": "cursor/MCP Server Registration/demo",
                    "identity_key": "cursor|mcp server registration|demo",
                    "host": "cursor",
                    "digest": "d1",
                    "fingerprint": "fp1",
                }
            ],
        }

    delta = diff_authority_locks(_lock(floating), _lock(swapped))
    assert delta_label(delta["summary"]) == "GROWTH"
    assert delta["summary"]["replacements"] >= 1
    assert delta["changes"]["changed"][0]["change_class"] in {"replacement", "mixed"}
    assert delta_max_reach_tier(delta) >= TIER_FAIL

    pin_delta = diff_authority_locks(_lock(floating), _lock(pinned))
    assert delta_label(pin_delta["summary"]) == "REDUCTION"
    assert pin_delta["changes"]["changed"][0]["change_class"] == "reduction"


def test_auct030_same_package_pin_from_json_mcp(tmp_path: Path):
    """Real JSON MCP pin tightening with package_stem is REDUCTION end-to-end."""
    from auctelis.authority_lock import delta_label

    root = tmp_path / "repo"
    _repo_with_mcp(
        root,
        {"linear": {"command": "npx", "args": ["-y", "@linear/mcp"]}},
    )
    _, base = write_authority_lock(root, accept_gated=True)
    rec = next(r for r in base["records"] if r["name"] == "linear")
    assert rec.get("package_stem") == "@linear/mcp"
    _repo_with_mcp(
        root,
        {"linear": {"command": "npx", "args": ["-y", "@linear/mcp@1.2.3"]}},
    )
    head = build_authority_lock(root)
    delta = diff_authority_locks(base, head)
    assert delta_label(delta["summary"]) == "REDUCTION"
    assert delta["changes"]["changed"][0]["change_class"] == "reduction"


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
    assert delta["summary"]["strict_drift_only"] is True


def test_auct034_strict_drift_only_quiet_for_non_hook(tmp_path: Path):
    """AUCT-034: non-Hook representation drift is advisory unless strict_digests."""
    root = tmp_path / "repo"
    _repo_with_mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    write_authority_lock(root, accept_gated=True)
    (root / ".cursor" / "mcp.json").rename(root / ".cursor" / "mcp_moved.json")
    report, code = check_locked(root)
    assert code == 0
    assert report["ok"] is True
    assert report.get("strict_drift_only") is True
    assert "representation digest drift only" in str(report.get("advisory") or "")
    report_s, code_s = check_locked(root, strict_digests=True)
    assert code_s == 1
    assert report_s["ok"] is False


def test_auct034_hook_representation_not_quiet():
    """AUCT-034: Hook body digest edits are never strict_drift_only."""
    base = {
        "version": 1,
        "records": [
            {
                "identity_key": "cursor|hook|demo",
                "host": "cursor",
                "kind": "Hook",
                "name": "demo",
                "path": ".cursor/hooks.json",
                "digest": "aaa",
                "script_digest": "aaa",
                "fingerprint": "fp1",
                "pin_state": "unknown",
                "approval_posture": "unknown",
                "capabilities": [],
                "destinations": [],
                "env_keys": [],
            }
        ],
    }
    head = {
        "version": 1,
        "records": [
            {
                **base["records"][0],
                "digest": "bbb",
                "script_digest": "bbb",
                "fingerprint": "fp2",
            }
        ],
    }
    d = diff_authority_locks(base, head)
    assert d["summary"]["authority_changed"] is True
    assert d["changes"]["changed"][0]["change_class"] == "representation"
    assert d["summary"]["strict_drift_only"] is False


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
    from auctelis_devtools.cli import main_dev

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
