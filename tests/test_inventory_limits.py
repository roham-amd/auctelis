"""AUCT-008 — monorepo-safe walk limits."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.gate import run_gate
from auctelis.inventory.collector import collect_inventory
from auctelis.inventory.limits import CollectorLimits, resolve_collector_limits
from auctelis.lock_io import empty_authority_lock


def _mcp(root: Path) -> None:
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": {"demo": {"command": "node", "args": ["a.js"]}}}) + "\n",
        encoding="utf-8",
    )


def test_5500_files_does_not_truncate_by_default(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    bulk = root / "bulk"
    bulk.mkdir()
    for i in range(5500):
        (bulk / f"f{i}.txt").write_text("x\n", encoding="utf-8")
    _mcp(root)
    result = collect_inventory(root)
    assert result.tree_summary.get("truncated") is False
    assert result.tree_summary.get("file_count", 0) >= 5501


def test_auctelis_max_files_env_triggers_truncation(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    bulk = root / "bulk"
    bulk.mkdir()
    for i in range(150):
        (bulk / f"f{i}.txt").write_text("x\n", encoding="utf-8")
    _mcp(root)
    monkeypatch.setenv("AUCTELIS_MAX_FILES", "100")
    result = collect_inventory(root, limits=resolve_collector_limits())
    assert result.tree_summary.get("truncated") is True

    base = tmp_path / "base.lock"
    base.write_text(json.dumps(empty_authority_lock()), encoding="utf-8")
    report, code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        comment_only=False,
        trust_head_codeowners=True,
    )
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert "AUCTELIS_MAX_FILES" in str(report.get("error") or "")


def test_resolve_collector_limits_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("AUCTELIS_MAX_FILES", "10")
    limits = resolve_collector_limits(max_files=99)
    assert limits.max_files == 99
    assert isinstance(limits, CollectorLimits)
