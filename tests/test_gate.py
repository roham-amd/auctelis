"""authdiff gate — base lock + GitHub-native approval."""

from __future__ import annotations

import json
from pathlib import Path

from authdiff.cli import main
from authdiff.gate import (
    github_native_approval_present,
    parse_codeowners_for_path,
    render_gate_report,
    run_gate,
)


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


def test_github_native_approval_any_reviewer():
    assert github_native_approval_present(approvers=["@alice"])
    assert not github_native_approval_present(approvers=[])


def test_gate_blocks_addition_until_approved(tmp_path: Path):
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
    report, code = run_gate(root, base_lock=base)
    assert code == 1
    assert report["needs_approval"] is True
    assert report["verdict"] == "NEEDS_APPROVAL"
    assert "@sec-owners" in report["required_owners"]
    assert "addition" in render_gate_report(report).lower() or report["lines"]

    # Any APPROVED identity works once CODEOWNERS covers the lock (native model).
    report2, code2 = run_gate(root, base_lock=base, approved_by=["@alice"])
    assert code2 == 0
    assert report2["approved"] is True
    assert report2["verdict"] == "PASS"


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
    assert main(["gate", str(root), "--base-lock", str(base)]) == 1
    assert main(["gate", str(root), "--base-lock", str(base), "--approved-by", "@owner"]) == 0


def test_same_name_launcher_swap_is_replacement(tmp_path: Path):
    root = tmp_path / "swap"
    _mcp(root, {"pkg": {"command": "npx", "args": ["-y", "pkg@1.0.0"]}})
    (root / ".github").mkdir(parents=True)
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    _mcp(root, {"pkg": {"command": "npx", "args": ["-y", "pkg@9.9.9"]}})
    report, code = run_gate(root, base_lock=base)
    assert code == 1
    assert report["needs_approval"] is True
    classes = [
        c.get("change_class")
        for c in (report.get("delta") or {}).get("changes", {}).get("changed", [])
    ]
    assert "replacement" in classes or report["meaningful_authority_change"]
