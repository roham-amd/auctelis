"""``diff --base`` when tree-truth extraction is unavailable."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from auctelis.cli import main
from auctelis.diff_base import run_diff_base


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")


def _write_mcp(root: Path, servers: dict) -> None:
    path = root / ".cursor" / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def _commit(root: Path, message: str) -> None:
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", message)


@pytest.fixture
def no_tree_extract(monkeypatch):
    """Simulate a failed detached-worktree extract (git worktree unavailable)."""
    monkeypatch.setattr("auctelis.diff_base._extract_tree_authority", lambda *a, **k: None)


def test_committed_lock_fallback_passes_when_unchanged(tmp_path: Path, no_tree_extract):
    root = tmp_path / "repo"
    _init_repo(root)
    _write_mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    assert main(["lock", str(root)]) == 0
    _commit(root, "base with lock")

    text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert payload["baseline_state"] == "present"
    assert payload["verdict"] == "PASS"
    assert payload["base_lock_hash"]
    assert code == 0
    assert "no authority change" in text


def test_committed_lock_fallback_detects_growth(tmp_path: Path, no_tree_extract):
    root = tmp_path / "repo"
    _init_repo(root)
    _write_mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    assert main(["lock", str(root)]) == 0
    _commit(root, "base with lock")
    _write_mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )

    _text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert payload["baseline_state"] == "present"
    assert payload["verdict"] == "NEEDS_REVIEW"
    assert payload["label"] == "GROWTH"
    assert code == 1


def test_absent_baseline_reports_absolute_head_reach(tmp_path: Path, no_tree_extract):
    root = tmp_path / "repo"
    _init_repo(root)
    _write_mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    _commit(root, "mcp without lock")

    text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert payload["baseline_state"] == "absent"
    assert payload["verdict"] == "BASELINE_NEEDED"
    assert payload["label"] == "NONE"
    assert code == 0
    assert "none at the base ref" in text
    assert "BASELINE_NEEDED" in text


def test_absent_baseline_on_empty_tree_is_pass(tmp_path: Path, no_tree_extract):
    root = tmp_path / "repo"
    _init_repo(root)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _commit(root, "empty authority")

    _text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert payload["baseline_state"] == "absent"
    assert payload["verdict"] == "PASS"
    assert code == 0
