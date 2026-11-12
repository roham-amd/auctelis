"""authdiff gate — base lock + CODEOWNERS + lock-only growth labels."""

from __future__ import annotations

import json
from pathlib import Path

from authdiff.cli import main
from authdiff.gate import parse_codeowners_for_path, render_gate_report, run_gate


def _mcp(root: Path, servers: dict) -> None:
    path = root / ".cursor" / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def test_parse_codeowners_last_match_wins():
    text = """
* @everyone
AUTHORITY.lock @sec-owners @alice
.authdiff.yml @sec-owners
"""
    assert parse_codeowners_for_path(text) == ["@sec-owners", "@alice"]


def test_gate_growth_passes_with_codeowners(tmp_path: Path):
    """Lock-only: growth is labeled; GitHub CODEOWNERS/rulesets enforce review."""
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    (root / ".github").mkdir(parents=True)
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @sec-owners\n", encoding="utf-8")
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")

    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    report, code = run_gate(root, base_lock=base, check_ruleset=False)
    assert code == 0
    assert report["needs_approval"] is True
    assert report["label"] == "GROWTH"
    assert report["verdict"] == "PASS"
    assert "@sec-owners" in report["required_owners"]
    assert "GROWTH" in render_gate_report(report)


def test_gate_growth_fails_without_codeowners(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    report, code = run_gate(root, base_lock=base, check_ruleset=False)
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert report.get("owners_present") is False
    assert report["label"] == "GROWTH"


def test_gate_cli(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    (root / ".github").mkdir(parents=True)
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @owner\n", encoding="utf-8")
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_bytes((root / "AUTHORITY.lock").read_bytes())
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    assert main(["gate", str(root), "--base-lock", str(base), "--skip-ruleset-check"]) == 0


def test_same_name_launcher_swap_is_replacement(tmp_path: Path):
    root = tmp_path / "swap"
    _mcp(root, {"pkg": {"command": "npx", "args": ["-y", "pkg@1.0.0"]}})
    (root / ".github").mkdir(parents=True)
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    _mcp(root, {"pkg": {"command": "npx", "args": ["-y", "pkg@9.9.9"]}})
    report, code = run_gate(root, base_lock=base, check_ruleset=False)
    assert code == 0
    assert report["needs_approval"] is True
    assert report["label"] == "GROWTH"
    classes = [
        c.get("change_class")
        for c in (report.get("delta") or {}).get("changes", {}).get("changed", [])
    ]
    assert "replacement" in classes or report["meaningful_authority_change"]
