"""Week-1 gate fixes from the strategic review apply pass."""

from __future__ import annotations

import json
from pathlib import Path

from authdiff.authority_lock import build_authority_lock, write_authority_lock
from authdiff.cli import main
from authdiff.cli.dispatch import _init_gate_templates
from authdiff.export.pr_comment import escape_markdown, render_authority_diff_comment
from authdiff.policy import load_policy


def test_policy_parser_empty_flow_list_and_comments(tmp_path: Path):
    path = tmp_path / ".authdiff.yml"
    path.write_text(
        """
version: 1
policy:
  mode: advisory  # day-one
  fail_on: never
  ignore: []
  require_review: [remote_mcp_endpoint, unpinned_mcp]
""",
        encoding="utf-8",
    )
    policy = load_policy(path)
    assert policy.mode == "advisory"
    assert policy.fail_on == "never"
    assert policy.suppressions == []
    assert policy.require_review == ["remote_mcp_endpoint", "unpinned_mcp"]


def test_ci_init_template_loads_and_round_trips(tmp_path: Path):
    policy_body, _workflow, _owners = _init_gate_templates()
    path = tmp_path / ".authdiff.yml"
    path.write_text(policy_body, encoding="utf-8")
    policy = load_policy(path)
    assert policy.mode == "advisory"
    assert policy.suppressions == []


def test_ci_init_requires_owner_and_writes_loadable_policy(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["ci", "init", str(root)]) == 2  # missing --owner
    assert main(["ci", "init", str(root), "--owner", "@YOUR_TEAM"]) == 2
    assert main(["ci", "init", str(root), "--owner", "@sec-owners"]) == 0
    policy = load_policy(root / ".authdiff.yml")
    assert policy.mode == "advisory"
    owners = (root / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "@sec-owners" in owners
    assert "@YOUR_TEAM" not in owners
    assert (root / "AUTHORITY.lock").is_file()


def test_lock_refuses_gated_without_accept(tmp_path: Path):
    root = tmp_path / "vuln"
    # Minimal copy: mcp with literal secret + floating launcher.
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
    assert main(["lock", str(root)]) == 1
    assert not (root / "AUTHORITY.lock").exists()
    assert main(["lock", str(root), "--accept-gated", "--approval", "@owner"]) == 0
    assert (root / "AUTHORITY.lock").is_file()


def test_lock_hash_stable_across_path_and_commit(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"x": {"command": "node", "args": ["x.js"]}}}),
        encoding="utf-8",
    )
    _, lock_a = write_authority_lock(root)
    assert "repository" not in lock_a
    # Re-lock with a fake commit change must keep the sealed hash.
    from authdiff.security import engine as engine_mod

    real = engine_mod.run_security_scan

    def with_commit(path):
        scan = real(path)
        object.__setattr__(scan, "commit", "deadbeef")
        return scan

    monkeypatch.setattr(engine_mod, "run_security_scan", with_commit)
    from authdiff import authority_lock as lock_mod

    monkeypatch.setattr(lock_mod, "run_security_scan", with_commit)
    lock_b = build_authority_lock(root)
    assert lock_a["lock_hash"] == lock_b["lock_hash"]
    assert lock_b.get("audited_commit") == "deadbeef"


def test_pr_comment_advisory_and_url_host(tmp_path: Path):
    findings = {
        "findings": [
            {
                "finding_id": "F-001",
                "rule_id": "AUTHDIFF-RULE-012",
                "severity": "CRITICAL",
                "title": "Literal secret",
                "finding_class": "SECURITY_FINDING",
                "evidence_ids": ["E-1"],
                "evidence_strength": "LITERAL_CONFIG",
                "entry_point": ".cursor/mcp.json:4",
            },
            {
                "finding_id": "F-002",
                "rule_id": "AUTHDIFF-RULE-011",
                "severity": "HIGH",
                "title": "Floating launcher",
                "finding_class": "SECURITY_FINDING",
                "evidence_ids": ["E-2"],
                "evidence_strength": "LITERAL_CONFIG",
            },
        ],
        "coverage": {"component_counts_by_maturity": {"SUPPORTED": 4}},
        "evidence_registry": [
            {"evidence_id": "E-1", "file_path": ".cursor/mcp.json", "line_start": 4}
        ],
    }
    comment = render_authority_diff_comment(findings, policy_mode="advisory")
    assert "ADVISORY (would BLOCK)" in comment
    assert "ADVISORY: would BLOCK" in comment
    # CRITICAL must lead over HIGH.
    crit = comment.index("F-001")
    high = comment.index("F-002") if "F-002" in comment else crit
    assert crit <= high
    escaped = escape_markdown("reaches http://analytics.example.net/mcp, passes GITHUB_TOKEN")
    assert "`analytics.example.net`" in escaped
    assert "http://" not in escaped
    assert "/mcp" not in escaped


def test_base_lock_fails_on_addition(tmp_path: Path):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}),
        encoding="utf-8",
    )
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "a": {"command": "node", "args": ["a.js"]},
                    "b": {"command": "node", "args": ["b.js"]},
                }
            }
        ),
        encoding="utf-8",
    )
    code = main(
        [
            "scan",
            str(root),
            "-o",
            str(tmp_path / "out"),
            "--fail-on",
            "never",
            "--base-lock",
            str(base),
        ]
    )
    assert code == 1
    delta = json.loads((tmp_path / "out" / "base-lock-delta.json").read_text(encoding="utf-8"))
    assert delta["summary"]["additions"] >= 1
    comment = (tmp_path / "out" / "pr-comment.md").read_text(encoding="utf-8")
    assert "addition" in comment.lower()


def test_workflows_not_double_registered(tmp_path: Path):
    from authdiff.inventory.collector import collect_inventory

    root = tmp_path / "repo"
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(
        "name: ci\non: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - run: echo hi\n",
        encoding="utf-8",
    )
    inv = collect_inventory(root)
    types = [
        str(c.get("type") or "")
        for c in inv.components
        if str(c.get("repository_path") or "").endswith("ci.yml")
    ]
    assert types.count("CI Workflow") == 1
    assert "Automation / Workflow" not in types
