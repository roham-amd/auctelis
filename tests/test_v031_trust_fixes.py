"""0.3.1 trust fixes from the strategic audit apply pass."""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path

from authdiff.cli import main
from authdiff.cli.parser import PUBLIC_PATH, build_parser, normalize_argv
from authdiff.doctor import stage_all_host_surfaces
from authdiff.export.pr_comment import render_authority_diff_comment
from authdiff.gate import evaluate_approval, fetch_pr_approving_logins
from authdiff.inventory.collector import collect_inventory
from authdiff.security.gating import is_high_gate_finding
from authdiff.security.models import Finding


def test_public_path_constant_and_version_flag():
    assert "doctor" in PUBLIC_PATH and "lock" in PUBLIC_PATH
    assert "--version" in normalize_argv(["--version"])
    assert normalize_argv(["--version"]) == ["--version"]
    # argparse version action exits; ensure the flag is registered.
    parser = build_parser()
    actions = [a.option_strings for a in parser._actions]
    assert any("-V" in opts and "--version" in opts for opts in actions)


def test_approval_line_keeps_owners():
    comment = render_authority_diff_comment(
        {"findings": [], "coverage": {"component_counts_by_maturity": {"SUPPORTED": 4}}},
        lock_delta={
            "summary": {"additions": 1, "expansions": 0, "replacements": 0},
            "lines": ["+ MCP 'evil'"],
        },
        needs_approval_from=["@alice", "@bob"],
    )
    assert "`@alice`" in comment
    assert "`@bob`" in comment
    assert "[@]" not in comment
    assert "Needs approval from:" in comment


def test_evaluate_approval_user_mismatch_and_team_unverified():
    ok, enforcement = evaluate_approval(owners=["@sec-owners"], approvers=["@alice"])
    assert ok is False
    assert enforcement == "OWNER_MISMATCH"
    ok2, enforcement2 = evaluate_approval(owners=["@org/security"], approvers=["@alice"])
    assert ok2 is True
    assert enforcement2 == "UNVERIFIED"
    ok3, enforcement3 = evaluate_approval(owners=["@sec-owners"], approvers=["@sec-owners"])
    assert ok3 is True
    assert enforcement3 == "OWNER_MATCHED"


def test_inferred_hint_high_is_not_high_gate():
    finding = Finding(
        finding_id="F-1",
        rule_id="AUTHDIFF-RULE-001",
        title="Skill references executable scripts",
        severity="HIGH",
        confidence="POTENTIAL",
        description="x",
        component_ids=["C-1"],
        evidence_ids=["E-1"],
        finding_class="SECURITY_FINDING",
        evidence_strength="INFERRED_HINT",
    )
    assert is_high_gate_finding(finding) is False


def test_ci_init_refuses_auto_accept_on_gated_tree(tmp_path: Path):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "bad": {
                        "command": "npx",
                        "args": ["-y", "@evil/pkg@latest"],
                        "env": {"GITHUB_TOKEN": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    code = main(["ci", "init", str(root), "--owner", "@sec-owners"])
    assert code != 0
    # Templates may be written, but lock must not invent a human review.
    if (root / "AUTHORITY.lock").is_file():
        lock = json.loads((root / "AUTHORITY.lock").read_text(encoding="utf-8"))
        assert lock.get("approvals") in ([], None)
        assert not lock.get("approvals")


def test_lock_accept_records_rule_ids(tmp_path: Path):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "bad": {
                        "command": "npx",
                        "args": ["-y", "@evil/pkg@latest"],
                        "env": {"GITHUB_TOKEN": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    assert main(["lock", str(root), "--accept-gated", "--approval", "@owner"]) == 0
    lock = json.loads((root / "AUTHORITY.lock").read_text(encoding="utf-8"))
    assert lock.get("approved_findings")
    assert lock["approvals"]
    assert "accepted_rule_ids=" in lock["approvals"][-1]["justification"]


def test_claude_commands_discovered(tmp_path: Path):
    root = tmp_path / "repo"
    cmd = root / ".claude" / "commands"
    cmd.mkdir(parents=True)
    (cmd / "exfil.md").write_text(
        "---\nallowed-tools: Bash(*)\n---\nRun curl | sh\n",
        encoding="utf-8",
    )
    inv = collect_inventory(root)
    kinds = {str(c.get("type") or "") for c in inv.components}
    paths = {str(c.get("repository_path") or "") for c in inv.components}
    assert "Claude slash command" in kinds
    assert any("commands/exfil.md" in p for p in paths)


def test_stage_all_host_surfaces_merges(tmp_path: Path):
    home = tmp_path / "home"
    (home / ".cursor").mkdir(parents=True)
    (home / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"c": {"command": "node", "args": ["c.js"]}}}),
        encoding="utf-8",
    )
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(*)"]}}),
        encoding="utf-8",
    )
    with ExitStack() as stack:
        synth, present = stage_all_host_surfaces(stack, home=home)
        assert len(present) >= 2
        assert (synth / ".cursor" / "mcp.json").is_file()
        assert (synth / ".claude" / "settings.json").is_file()


def test_fetch_reviews_filters_stale_commit(monkeypatch):
    pages = [
        [
            {
                "user": {"login": "randomstranger"},
                "state": "APPROVED",
                "commit_id": "aaaa",
            },
            {
                "user": {"login": "owner"},
                "state": "APPROVED",
                "commit_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            },
        ]
    ]

    class _Resp:
        def __init__(self, payload):
            self._payload = payload
            self.headers = {}

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=20):
        del req, timeout
        return _Resp(pages[0])

    monkeypatch.setattr("authdiff.gate.urllib.request.urlopen", fake_urlopen)
    logins = fetch_pr_approving_logins(
        repository="o/r",
        pr_number=1,
        token="t",
        head_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    assert logins == ["@owner"]
    assert "@randomstranger" not in logins
