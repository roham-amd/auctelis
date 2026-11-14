"""Week 2-3: default path excludes + doctor --since-lock."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.cli import main
from auctelis.doctor import run_doctor_since_lock
from auctelis.inventory.collector import collect_inventory


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
    names = {str(c.get("name") or "") for c in inv.components}
    paths = {str(c.get("repository_path") or "") for c in inv.components}
    assert "real" in names
    assert "evil" not in names
    assert not any("tests" in p.replace("\\", "/") for p in paths)


def test_include_fixtures_flag(tmp_path: Path):
    root = tmp_path / "repo"
    evil = root / "tests" / ".cursor"
    evil.mkdir(parents=True)
    (evil / "mcp.json").write_text(
        json.dumps({"mcpServers": {"evil": {"command": "node", "args": ["e.js"]}}}),
        encoding="utf-8",
    )
    assert (
        main(["scan", str(root), "-o", str(tmp_path / "out1"), "--fail-on", "never"])
        == 0
    )
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
    default_names = {
        str(c.get("name") or "")
        for c in json.loads(
            (tmp_path / "out1" / "inventory.json").read_text(encoding="utf-8")
        ).get("components", [])
    }
    included_names = {
        str(c.get("name") or "")
        for c in json.loads(
            (tmp_path / "out2" / "inventory.json").read_text(encoding="utf-8")
        ).get("components", [])
    }
    assert "evil" not in default_names
    assert "evil" in included_names


def test_default_excludes_skip_eval_fixtures(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".cursor").mkdir(parents=True)
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"real": {"command": "node", "args": ["r.js"]}}}),
        encoding="utf-8",
    )
    fixture = root / "eval" / "configs" / "cfg-bad" / ".cursor"
    fixture.mkdir(parents=True)
    (fixture / "mcp.json").write_text(
        json.dumps({"mcpServers": {"fixture": {"command": "node", "args": ["f.js"]}}}),
        encoding="utf-8",
    )
    inv = collect_inventory(root)
    paths = {str(c.get("repository_path") or "") for c in inv.components}
    assert not any("eval" in p.replace("\\", "/") for p in paths)


def test_doctor_since_lock_missing(tmp_path: Path):
    text, code = run_doctor_since_lock(
        home=tmp_path / "home", lock_file=tmp_path / "missing.lock"
    )
    # No lock is a valid empty baseline (first run), not an error.
    assert code == 0
    assert "none yet" in text
    assert "0 MCP" in text
