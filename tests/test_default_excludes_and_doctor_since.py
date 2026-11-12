"""Week 2-3: default path excludes + doctor --since-lock."""

from __future__ import annotations

import json
from pathlib import Path

from authdiff.cli import main
from authdiff.doctor import run_doctor_since_lock
from authdiff.inventory.collector import collect_inventory


def test_default_excludes_skip_tests_dir(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".cursor").mkdir(parents=True)
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"real": {"command": "node", "args": ["r.js"]}}}),
        encoding="utf-8",
    )
    evil = root / "tests" / "fixtures" / ".cursor"
    evil.mkdir(parents=True)
    (evil / "mcp.json").write_text(
        json.dumps({"mcpServers": {"evil": {"command": "node", "args": ["e.js"]}}}),
        encoding="utf-8",
    )
    inv = collect_inventory(root)
    paths = {str(c.get("repository_path") or "") for c in inv.components}
    assert any("real" in p or ".cursor/mcp.json" in p.replace("\\", "/") for p in paths) or any(
        "real" in str(c) for c in inv.components
    )
    assert not any("tests" in p.replace("\\", "/") for p in paths)


def test_include_fixtures_flag(tmp_path: Path):
    root = tmp_path / "repo"
    evil = root / "tests" / ".cursor"
    evil.mkdir(parents=True)
    (evil / "mcp.json").write_text(
        json.dumps({"mcpServers": {"evil": {"command": "node", "args": ["e.js"]}}}),
        encoding="utf-8",
    )
    assert main(["scan", str(root), "-o", str(tmp_path / "out1"), "--fail-on", "never"]) == 0
    assert (
        main(
            [
                "scan",
                str(root),
                "-o",
                str(tmp_path / "out2"),
                "--fail-on",
                "never",
                "--include-fixtures",
            ]
        )
        == 0
    )


def test_doctor_since_lock_missing(tmp_path: Path):
    text, code = run_doctor_since_lock(home=tmp_path / "home", lock_file=tmp_path / "missing.lock")
    assert code == 1
    assert "No lock" in text
