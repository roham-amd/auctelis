"""Days 6-30 product-review deliverables: ceremony, strict ruleset, field diffs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from auctelis.authority_lock import (
    diff_authority_locks,
    field_level_change_bits,
    render_lock_diff_lines,
)
from auctelis.cli import main
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.gate import (
    adoption_bootstrap_verdict,
    protection_status,
    render_gate_report,
    run_gate,
)


def _mcp(root: Path, servers: dict) -> None:
    path = root / ".cursor" / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def _owners(root: Path) -> None:
    (root / ".github").mkdir(parents=True, exist_ok=True)
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")


def _rec(
    name: str,
    *,
    caps: list[str] | None = None,
    dest: list[str] | None = None,
    env: list[str] | None = None,
    pin: str = "pinned",
    approval: str = "prompt",
    path: str = ".cursor/mcp.json",
) -> dict[str, Any]:
    return {
        "id": f"cursor/MCP Server Registration/{name}@{path}",
        "identity_key": f"cursor|mcp server registration|{name}",
        "host": "cursor",
        "kind": "MCP Server Registration",
        "name": name,
        "path": path,
        "digest": "d1",
        "fingerprint": "fp1",
        "pin_state": pin,
        "approval_posture": approval,
        "capabilities": caps or ["execute_commands"],
        "destinations": dest or [],
        "env_keys": env or [],
        "launcher": "npx",
        "args_digest": "abc123",
        "url_host": "",
    }


def test_adoption_ceremony_distinct_from_growth_gate():
    adopted = adoption_bootstrap_verdict(base_lock_present=False, head_lock_present=True)
    assert adopted["verdict"] == "BASELINE_ADOPTED"
    assert adopted["ceremony"] == "baseline_adopted"
    assert adopted["ok"] is True

    closed = adoption_bootstrap_verdict(base_lock_present=False, head_lock_present=False)
    assert closed["ok"] is False
    assert closed["verdict"] == "FAIL_CLOSED"

    growth = adoption_bootstrap_verdict(base_lock_present=True, head_lock_present=True)
    assert growth["ceremony"] == "growth_gate"
    assert growth["verdict"] == "GROWTH_GATE"


def test_protection_status_labels():
    assert protection_status("OK", needs_approval=True) == "verified"
    assert protection_status("UNVERIFIED", needs_approval=True) == "unverified"
    assert protection_status("MISSING", needs_approval=True) == "missing"
    assert protection_status("OK", needs_approval=False) == "n/a"


def test_strict_ruleset_fails_unverified_growth(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    _owners(root)
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
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    report, code = run_gate(root, base_lock=base, strict_ruleset=True)
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert report["ruleset"] == "UNVERIFIED"
    assert report["protection"] == "unverified"
    assert report["strict_ruleset"] is True

    soft, soft_code = run_gate(root, base_lock=base)
    assert soft_code == 0
    assert soft["verdict"] == "PASS"
    assert soft["protection"] == "unverified"
    assert "PASS / protection unverified" in render_gate_report(soft)


def test_ruleset_missing_fails_growth(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    _owners(root)
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
    with patch("auctelis.gate.check_code_owner_ruleset", return_value=("MISSING", "no ruleset")):
        report, code = run_gate(root, base_lock=base)
    assert code == 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert report["protection"] == "missing"


def test_ruleset_ok_marks_protection_verified(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    _owners(root)
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
    with patch(
        "auctelis.gate.check_code_owner_ruleset",
        return_value=("OK", "ruleset requires code-owner review"),
    ):
        report, code = run_gate(root, base_lock=base)
    assert code == 0
    assert report["protection"] == "verified"
    assert "PASS / protection verified" in render_gate_report(report)


def test_field_level_lock_diff_lines_and_pr_comment():
    before = _rec("echo", caps=["execute_commands"], pin="pinned")
    after = _rec(
        "echo",
        caps=["execute_commands", "network"],
        dest=["api.example"],
        env=["TOKEN"],
        pin="floating",
        approval="auto",
    )
    bits = field_level_change_bits(before, after)
    joined = "; ".join(bits)
    assert "capabilities +[network]" in joined
    assert "destinations +[api.example]" in joined
    assert "env_keys +[TOKEN]" in joined
    assert "pin_state: pinned → floating" in joined
    assert "approval_posture: prompt → auto" in joined

    base = {"version": 1, "policy_hash": "p1", "records": [before], "mcp_tools": {}}
    head = {"version": 1, "policy_hash": "p1", "records": [after], "mcp_tools": {}}
    delta = diff_authority_locks(base, head)
    lines = delta["lines"]
    assert any("expansion" in line and "→" in line for line in lines)
    assert any("@ .cursor/mcp.json" in line for line in lines)

    comment = render_authority_diff_comment(
        {"findings": [], "coverage": {"not_verified": ["runtime"]}},
        lock_delta=delta,
        needs_approval_from=["@sec"],
    )
    assert "Authority delta" in comment
    assert "expansion" in comment
    assert "→" in comment or "capabilities" in comment


def test_gate_cli_strict_ruleset_flag(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    _owners(root)
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
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    code = main(["gate", str(root), "--base-lock", str(base), "--strict-ruleset"])
    out = capsys.readouterr().out
    assert code == 1
    assert "NEEDS_REVIEW" in out or "UNVERIFIED" in out or "strict" in out.lower()


def test_render_lock_diff_addition_includes_path():
    lines = render_lock_diff_lines(
        added=[_rec("new", dest=["h.example"], path="cfg/mcp.json")],
        removed=[],
        changed=[],
    )
    assert lines
    assert "@ cfg/mcp.json" in lines[0]
    assert "reaches h.example" in lines[0]


def test_pilot_tracker_files_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "pilots" / "TRACKER.md").is_file()
    assert (root / "docs" / "pilots" / "README.md").is_file()
    assert (root / "eval" / "pilot-metrics.csv").is_file()
    assert (root / ".github" / "ISSUE_TEMPLATE" / "pilot.yml").is_file()
    tracker = (root / "docs" / "pilots" / "TRACKER.md").read_text(encoding="utf-8")
    assert "retained_30d" in tracker
    metrics = (root / "eval" / "pilot-metrics.csv").read_text(encoding="utf-8")
    assert "install_to_first_lock_minutes" in metrics
