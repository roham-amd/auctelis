"""Gate Zero 30-day plan — adoption, evidence, diff --base, gate trust."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_card import changed_card, record_card, removed_card, why_record
from auctelis.authority_lock import write_authority_lock
from auctelis.check import build_check_report, render_check
from auctelis.cli import main
from auctelis.diff_base import run_diff_base
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.gate import adoption_bootstrap_verdict, run_gate


def _mcp(root: Path, servers: dict) -> None:
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": servers}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_check_match_prints_coverage_not_clearance(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"echo": {"command": "node", "args": ["a.js"]}})
    write_authority_lock(root, accept_gated=True)
    report, cards, _scan = build_check_report(root)
    text = render_check(report, cards)
    assert "matches" in text
    assert "SUPPORTED" in text or "PARTIAL" in text
    assert "not a security clearance" in text.lower()
    # Product check is inventory-only; advisory findings only appear when non-zero.
    assert "Gated findings:" not in text or "Advisory findings:" in text


def test_cards_include_path_and_evidence():
    record = {
        "kind": "MCP Server Registration",
        "name": "linear",
        "path": ".cursor/mcp.json",
        "url_host": "mcp.linear.app",
        "capabilities": ["access_network"],
        "pin_state": "floating",
        "evidence_strength": "LITERAL_CONFIG",
    }
    card = record_card(record)
    assert "@ .cursor/mcp.json" in card
    assert "LITERAL_CONFIG" in card

    host = {
        "kind": "host settings",
        "name": "claude",
        "path": ".claude/settings.json",
        "approval_posture": "bypass",
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert "@ .claude/settings.json" in record_card(host)

    removed = removed_card(record)
    assert "@ .cursor/mcp.json" in removed

    changed = changed_card(
        {
            "before": {**record, "capabilities": ["access_network"]},
            "after": {**record, "capabilities": ["access_network", "access_secrets"]},
        }
    )
    assert "@ .cursor/mcp.json" in changed
    assert "LITERAL_CONFIG" in changed

    why = "\n".join(why_record(record))
    assert "LITERAL_CONFIG" in why
    assert "INFERRED_HINT" not in why or "LITERAL_CONFIG" in why


def test_why_does_not_hardcode_literal_when_inferred():
    record = {
        "kind": "skill",
        "name": "x",
        "path": "skills/x/SKILL.md",
        "evidence_strength": "INFERRED_HINT",
    }
    why = "\n".join(why_record(record))
    assert "evidence: INFERRED_HINT" in why
    assert "evidence: LITERAL_CONFIG" not in why


def test_adoption_comment_never_pass():
    ceremony = adoption_bootstrap_verdict(base_lock_present=False, head_lock_present=True)
    assert ceremony["verdict"] == "BASELINE_ADOPTED"
    comment = render_authority_diff_comment(
        {"findings": [], "coverage": {}},
        verdict="BASELINE_ADOPTED",
    )
    assert "BASELINE_ADOPTED" in comment
    assert "**Verdict:** `PASS`" not in comment


def test_gate_rejects_directory_base_lock(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    report, code = run_gate(root, base_lock=tmp_path, check_ruleset=False)
    assert code == 2
    assert report["verdict"] == "FAIL_CLOSED"
    assert "directory" in str(report.get("error") or "").lower()


def test_gate_rejects_untrusted_head_codeowners(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    owners = root / ".github"
    owners.mkdir(parents=True)
    (owners / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    write_authority_lock(root, accept_gated=True)
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    report, code = run_gate(root, base_lock=base, check_ruleset=True, strict_ruleset=False)
    assert code == 1
    assert "trust-head-codeowners" in str(report.get("error") or "")


def test_diff_base_simulator(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    # Initialize a tiny git repo so git show works.
    import subprocess

    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True, capture_output=True)
    write_authority_lock(root, accept_gated=True)
    subprocess.run(
        ["git", "add", "AUTHORITY.lock", ".cursor"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(["git", "commit", "-m", "base"], cwd=root, check=True, capture_output=True)
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert payload["schema_version"] == "authority-diff/1"
    assert payload["label"] == "GROWTH"
    assert code == 1
    assert "Verdict:" in text


def test_ci_init_apply_merges_codeowners(tmp_path: Path):
    root = tmp_path / "repo"
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    owners = root / ".github"
    owners.mkdir(parents=True)
    (owners / "CODEOWNERS").write_text("# keep\nREADME.md @other\n", encoding="utf-8")
    code = main(["ci", "init", str(root), "--owner", "@sec-team", "--apply"])
    # May return 1 when ruleset cannot be verified (no token) — files must still merge.
    text = (owners / "CODEOWNERS").read_text(encoding="utf-8")
    assert "README.md @other" in text
    assert "AUTHORITY.lock @sec-team" in text
    assert code in {0, 1}


def test_action_tracks_base_lock_committed_for_baseline_adopted():
    action = (
        Path(__file__).resolve().parents[1] / ".github" / "actions" / "auctelis-gate" / "action.yml"
    ).read_text(encoding="utf-8")
    assert "base_lock_committed=false" in action
    assert "base_lock_committed=true" in action
    assert 'AUCTELIS_BASE_LOCK_COMMITTED:-true}" == "false"' in action
    assert 'auctelis lock "$AUCTELIS_PATH" --lock-file "$head_lock_path" --check' in action
    assert "BASELINE_ADOPTED refused — CODEOWNERS does not cover AUTHORITY.lock." in action
