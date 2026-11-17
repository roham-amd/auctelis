"""Trust-reset coverage for the 30-day product shrink (v0.8.1+)."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_card import delta_cards, evidence_label
from auctelis.authority_lock import (
    diff_authority_locks,
    normalize_lock_for_compare,
    write_authority_lock,
)
from auctelis.check import build_check_report, check_exit_code
from auctelis.cli.dispatch import (
    _find_existing_codeowners,
    _merge_codeowners_authority,
    _workflow_locked_state,
)
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.gate import (
    adoption_bootstrap_verdict,
    codeowners_covers_protection,
)
from auctelis.policy import load_policy


def test_enforce_never_stays_never(tmp_path: Path):
    path = tmp_path / ".auctelis.yml"
    path.write_text("version: 1\npolicy:\n  mode: enforce\n  fail_on: never\n", encoding="utf-8")
    assert load_policy(path).fail_on == "never"


def test_evidence_strength_survives_normalize_and_delta_cards():
    base = {
        "version": 1,
        "policy_hash": None,
        "records": [],
        "mcp_tools": {},
    }
    head = {
        "version": 1,
        "policy_hash": None,
        "mcp_tools": {},
        "records": [
            {
                "id": "cursor|mcp server registration|linear",
                "identity_key": "cursor|mcp server registration|linear",
                "host": "cursor",
                "kind": "MCP Server Registration",
                "name": "linear",
                "path": ".cursor/mcp.json",
                "digest": "sha256:abc",
                "fingerprint": "fp1",
                "pin_state": "floating",
                "approval_posture": "unknown",
                "capabilities": ["access_network", "invoke_tools"],
                "destinations": ["mcp.linear.app"],
                "env_keys": [],
                "permission_allows": [],
                "launcher": "npx",
                "args_digest": "sha256:args",
                "url_host": "mcp.linear.app",
                "script_digest": "",
                "evidence_strength": "LITERAL_CONFIG",
                "capability_origin": "DECLARED",
            }
        ],
    }
    normalized = normalize_lock_for_compare(head)
    assert normalized["records"][0]["evidence_strength"] == "LITERAL_CONFIG"
    delta = diff_authority_locks(base, head)
    cards = delta_cards(delta, limit=10)
    assert cards
    assert "LITERAL_CONFIG" in cards[0]
    assert evidence_label(delta["changes"]["added"][0]) == "LITERAL_CONFIG"


def test_pr_comment_shows_four_additions_and_names_network_only():
    base = {"version": 1, "policy_hash": None, "records": [], "mcp_tools": {}}
    records = []
    for i, (name, dest, caps, env) in enumerate(
        (
            ("alpha", "api.example.com", ["access_network"], []),
            ("beta", "", ["invoke_tools"], ["GITHUB_TOKEN"]),
            ("gamma", "hooks.example.com", ["access_network", "execute_commands"], []),
            ("delta", "cdn.example.com", ["access_network"], []),
        )
    ):
        records.append(
            {
                "id": f"cursor|mcp|{name}",
                "identity_key": f"cursor|mcp server registration|{name}",
                "host": "cursor",
                "kind": "MCP Server Registration",
                "name": name,
                "path": f".cursor/mcp-{i}.json",
                "digest": f"sha256:{i}",
                "fingerprint": f"fp{i}",
                "pin_state": "floating",
                "approval_posture": "unknown",
                "capabilities": caps,
                "destinations": [dest] if dest else [],
                "env_keys": env,
                "permission_allows": [],
                "launcher": "npx" if not dest else "",
                "args_digest": "",
                "url_host": dest,
                "script_digest": "",
                "evidence_strength": "LITERAL_CONFIG",
                "capability_origin": "DECLARED",
            }
        )
    head = {"version": 1, "policy_hash": None, "records": records, "mcp_tools": {}}
    delta = diff_authority_locks(base, head)
    cards = delta_cards(delta, limit=10, include_overflow_summary=True)
    assert len([c for c in cards if c.startswith("+")]) >= 4
    comment = render_authority_diff_comment(
        {"findings": [], "coverage": {}},
        lock_delta=delta,
        needs_approval_from=["@security"],
    )
    for name in ("alpha", "beta", "gamma", "delta"):
        assert name in comment


def test_adoption_requires_codeowners():
    ok = adoption_bootstrap_verdict(
        base_lock_present=False,
        head_lock_present=True,
        codeowners_covers=False,
        base_ref_resolved=True,
    )
    assert ok["ok"] is False
    assert ok["verdict"] == "NEEDS_REVIEW"

    bad_base = adoption_bootstrap_verdict(
        base_lock_present=False,
        head_lock_present=True,
        codeowners_covers=True,
        base_ref_resolved=False,
    )
    assert bad_base["ok"] is False
    assert bad_base["verdict"] == "FAIL_CLOSED"

    adopted = adoption_bootstrap_verdict(
        base_lock_present=False,
        head_lock_present=True,
        codeowners_covers=True,
        base_ref_resolved=True,
    )
    assert adopted["ok"] is True
    assert adopted["verdict"] == "BASELINE_ADOPTED"


def test_codeowners_protection_coverage(tmp_path: Path):
    text = (
        "AUTHORITY.lock @sec\n"
        ".auctelis.yml @sec\n"
        ".github/workflows/ @sec\n"
        ".github/actions/ @sec\n"
        ".github/CODEOWNERS @sec\n"
    )
    ok, missing = codeowners_covers_protection(text)
    assert ok, missing
    # With root scoping, lock-only trees need lock coverage; gate install needs more.
    root = tmp_path / "repo"
    root.mkdir()
    (root / "AUTHORITY.lock").write_text("{}\n", encoding="utf-8")
    (root / ".github").mkdir()
    (root / ".github" / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    ok_scoped, missing_scoped = codeowners_covers_protection(
        "AUTHORITY.lock @sec\n",
        root=root,
    )
    assert ok_scoped, missing_scoped
    wf = root / ".github" / "workflows"
    wf.mkdir()
    (wf / "auctelis-gate.yml").write_text("name: x\n", encoding="utf-8")
    ok_gate, missing_gate = codeowners_covers_protection("AUTHORITY.lock @sec\n", root=root)
    assert not ok_gate
    assert any("workflow" in m or "CODEOWNERS" in m for m in missing_gate)
    partial = "AUTHORITY.lock @sec\n"
    ok2, missing2 = codeowners_covers_protection(partial)
    assert not ok2
    assert missing2


def test_init_does_not_shadow_root_codeowners(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "CODEOWNERS").write_text("* @everyone\n", encoding="utf-8")
    found = _find_existing_codeowners(root)
    assert found == root / "CODEOWNERS"
    merged = _merge_codeowners_authority(
        (root / "CODEOWNERS").read_text(encoding="utf-8"),
        "@security",
    )
    assert "AUTHORITY.lock @security" in merged
    assert ".github/workflows/" in merged
    # Writing through merge path must not create .github/CODEOWNERS for detection.
    assert _find_existing_codeowners(root) == root / "CODEOWNERS"


def test_workflow_locked_state_reports_truth():
    body = (
        "jobs:\n  gate:\n    steps:\n"
        "      - uses: roham-amd/auctelis/.github/actions/auctelis-gate@v0.8.1\n"
        '        with:\n          locked: "false"\n'
    )
    has_gate, locked, pin = _workflow_locked_state(body)
    assert has_gate is True
    assert locked is False
    assert pin == "v0.8.1"


def test_lock_refuses_unparsed(tmp_path: Path):
    root = tmp_path / "broken"
    root.mkdir()
    mcp = root / ".cursor"
    mcp.mkdir()
    # Invalid JSON agent config — inventory should mark unparsed.
    (mcp / "mcp.json").write_text("{not-json", encoding="utf-8")
    try:
        write_authority_lock(root)
        raised = False
    except ValueError as exc:
        raised = True
        assert "unparsed" in str(exc).lower() or "could not be parsed" in str(exc).lower()
    assert raised


def test_check_needs_review_on_unparsed(tmp_path: Path):
    root = tmp_path / "broken"
    root.mkdir()
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text("{not-json", encoding="utf-8")
    # Empty valid lock so we are not first-run.
    empty_lock = {
        "version": 1,
        "product": "auctelis",
        "product_version": "0.0.0",
        "policy_hash": None,
        "records": [],
        "mcp_tools": {},
        "mcp_servers": {},
        "lock_hash": "0" * 32,
        "approvals": [],
        "approved_findings": [],
    }
    # Minimal valid seal — load_authority_lock may require schema; write via API if needed.
    from auctelis.lock_io import load_authority_lock

    lock_path = root / "AUTHORITY.lock"
    # Build a sealed empty lock from a clean sibling tree then copy hash pattern.
    clean = tmp_path / "clean"
    clean.mkdir()
    path, lock = write_authority_lock(clean)
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    load_authority_lock(lock_path)  # schema ok
    report, _cards, _scan = build_check_report(root, lock_file=lock_path)
    assert int(report.get("unparsed") or 0) >= 1
    assert report["verdict"] == "NEEDS_REVIEW"
    assert check_exit_code(report) == 1
    del empty_lock, path


def test_status_check_exits_nonzero_when_unarmed(tmp_path: Path):
    from auctelis.cli import main

    root = tmp_path / "empty"
    root.mkdir()
    assert main(["status", "--check", str(root)]) == 1


def test_status_check_armed_after_init(tmp_path: Path, monkeypatch):
    from auctelis.cli import main

    root = tmp_path / "repo"
    root.mkdir()
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text(
        '{"mcpServers":{"demo":{"command":"node","args":["x.js"]}}}',
        encoding="utf-8",
    )
    # Comment-only init is ready; enforce needs verified ruleset.
    assert main(["init", str(root), "--owner", "security"]) == 0
    assert (root / ".github" / "CODEOWNERS").is_file()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert main(["status", "--check", str(root)]) == 0
    assert main(["init", str(root), "--owner", "security", "--enforce", "--force"]) == 0
    assert main(["status", "--check", str(root)]) == 1
    # Verified ruleset + locked workflow → armed.
    monkeypatch.setattr(
        "auctelis.gate.check_code_owner_ruleset",
        lambda **_kwargs: ("OK", "ruleset requires code-owner reviews"),
    )
    assert main(["status", "--check", str(root)]) == 0


def test_init_merges_root_codeowners_without_shadow(tmp_path: Path):
    from auctelis.cli import main

    root = tmp_path / "repo"
    root.mkdir()
    (root / "CODEOWNERS").write_text("* @everyone\n", encoding="utf-8")
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text(
        '{"mcpServers":{"demo":{"command":"node","args":["x.js"]}}}',
        encoding="utf-8",
    )
    assert main(["init", str(root), "--owner", "security"]) == 0
    assert (root / "CODEOWNERS").is_file()
    assert not (root / ".github" / "CODEOWNERS").exists()
    text = (root / "CODEOWNERS").read_text(encoding="utf-8")
    assert "* @everyone" in text
    assert "AUTHORITY.lock @security" in text
    assert ".github/workflows/" in text


def test_lock_cli_refuses_unparsed(tmp_path: Path):
    from auctelis.cli import main

    root = tmp_path / "broken"
    root.mkdir()
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text("{not-json", encoding="utf-8")
    assert main(["lock", str(root)]) == 1
