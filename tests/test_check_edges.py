"""``auctelis check`` input validation, fail-closed output, and honesty branches."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.check import build_check_report, render_check, why_repo
from auctelis.cli import main


def _repo(root: Path, servers: dict | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": servers or {}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def test_check_missing_path_is_usage_error(tmp_path: Path, capsys):
    code = main(["check", str(tmp_path / "missing")])
    assert code == 2
    assert "not a directory" in capsys.readouterr().out


def test_check_file_path_does_not_silently_scan_empty(tmp_path: Path, capsys):
    target = tmp_path / "README.md"
    target.write_text("x\n", encoding="utf-8")
    code = main(["check", str(target)])
    assert code == 2
    assert "not a directory" in capsys.readouterr().out


def test_check_corrupt_lock_fails_closed_with_message(tmp_path: Path, capsys):
    root = _repo(tmp_path / "repo", {"a": {"command": "node", "args": ["a.js"]}})
    (root / "AUTHORITY.lock").write_text("{not json", encoding="utf-8")
    code = main(["check", str(root)])
    out = capsys.readouterr().out
    assert code == 2
    assert "auctelis check:" in out
    assert "Fail-closed: fix or reseal AUTHORITY.lock" in out


def test_check_first_run_with_unparsed_config_is_needs_review(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    cfg = root / ".cursor"
    cfg.mkdir(parents=True)
    (cfg / "mcp.json").write_text("{broken", encoding="utf-8")
    code = main(["check", str(root)])
    out = capsys.readouterr().out
    assert code == 1
    assert "NOT PARSED: 1" in out
    assert "NEEDS_REVIEW" in out


def test_check_representation_drift_is_visible_and_exit_1(tmp_path: Path, capsys):
    root = _repo(tmp_path / "repo", {"a": {"command": "node", "args": ["a.js"]}})
    assert main(["lock", str(root)]) == 0
    capsys.readouterr()
    # Same authority identity and fields; only the config path moved.
    (root / ".cursor" / "mcp.json").rename(root / ".cursor" / "mcp_example.json")
    code = main(["check", str(root)])
    out = capsys.readouterr().out
    assert code == 1
    assert "representation drift" in out


def test_check_invalid_baseline_is_usage_error(tmp_path: Path, capsys):
    root = _repo(tmp_path / "repo", {"a": {"command": "node", "args": ["a.js"]}})
    bad = tmp_path / "baseline.json"
    bad.write_text("[1, 2]\n", encoding="utf-8")
    code = main(
        [
            "check",
            str(root),
            "--report",
            str(tmp_path / "out"),
            "--baseline",
            str(bad),
        ]
    )
    assert code == 2
    assert "JSON object" in capsys.readouterr().out


def test_why_overflow_lists_more_matches(tmp_path: Path):
    servers = {f"skill-{i}": {"command": "node", "args": [f"{i}.js"]} for i in range(6)}
    root = _repo(tmp_path / "repo", servers)
    lines, code = why_repo("skill", root=root)
    assert code == 0
    text = "\n".join(lines)
    assert "… +1 more matches" in text


def test_render_check_error_keeps_lock_name(tmp_path: Path):
    root = _repo(tmp_path / "repo")
    (root / "AUTHORITY.lock").write_text("[]\n", encoding="utf-8")
    report, _cards, _scan = build_check_report(root)
    assert report["error"]
    text = render_check(report, [])
    assert "Fail-closed" in text
    assert "AUTHORITY.lock" in text
