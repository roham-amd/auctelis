"""AUCT-006 — lock deletion and truncation under enforce."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import write_authority_lock
from auctelis.gate import run_gate
from auctelis.inventory.coverage import count_truncation_events


def _mcp(root: Path, servers: dict) -> None:
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": servers}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_delete_lock_under_enforce_exits_needs_review(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(
        root,
        {
            "secret": {
                "command": "npx",
                "args": ["-y", "@evil/mcp"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "x"},
            }
        },
    )
    write_authority_lock(root)
    base = tmp_path / "base.lock"
    base.write_bytes((root / "AUTHORITY.lock").read_bytes())
    # Simulate PR that deletes the lock and keeps (or grows) authority.
    (root / "AUTHORITY.lock").unlink()
    report, code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=False,
        trust_head_codeowners=True,
    )
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert report["lock_tree_drift"] is True
    assert "absent on head" in (report.get("error") or "")


def test_delete_lock_comment_only_stays_green(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    write_authority_lock(root)
    base = tmp_path / "base.lock"
    base.write_bytes((root / "AUTHORITY.lock").read_bytes())
    (root / "AUTHORITY.lock").unlink()
    report, code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    assert code == 0
    assert report["ok"] is True


def test_count_truncation_events():
    counts = count_truncation_events(
        [
            {"type": "depth_limit", "path": "a"},
            {"type": "file_limit_reached", "path": "b"},
            {"type": "read_error", "path": "c"},
            {"type": "parse_error", "path": "d"},
        ]
    )
    assert counts == {"depth_limit": 1, "file_limit_reached": 1, "read_error": 1}


def test_truncation_under_enforce_needs_review(tmp_path: Path, monkeypatch):
    from dataclasses import replace

    from auctelis import gate as gate_mod

    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base, _ = write_authority_lock(root)

    real_inventory = gate_mod.run_authority_inventory

    def _truncated_scan(path):
        scan = real_inventory(path)
        coverage = dict(scan.coverage or {})
        events = list(coverage.get("parser_events") or [])
        events.append({"type": "file_limit_reached", "path": "."})
        coverage["parser_events"] = events
        coverage["file_limit_reached_count"] = 1
        coverage["truncated"] = True
        return replace(scan, coverage=coverage)

    monkeypatch.setattr(gate_mod, "run_authority_inventory", _truncated_scan)
    report, code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=False,
        trust_head_codeowners=True,
    )
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert "truncated" in (report.get("error") or "").lower()
