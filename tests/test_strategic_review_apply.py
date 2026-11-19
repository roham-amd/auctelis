"""Regression coverage for strategic review application (auctelis north-star)."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import (
    build_authority_lock,
    diff_authority_locks,
    write_authority_lock,
)
from auctelis.cli import main
from auctelis.cli.dispatch import _demo_target
from auctelis.cli.parser import CORE_PUBLIC_COMMANDS, build_parser
from auctelis.security.decision import authority_establishment, compute_decision
from auctelis.security.relationships import emit_relationships
from auctelis_research.scan import run_scan


def test_core_public_commands_are_the_first_screen():
    # Front door is repo Authority Diff. watch/allow/hook are archived.
    assert {
        "check",
        "lock",
        "ci",
        "gate",
        "diff",
        "why",
        "demo",
        "init",
        "status",
        "trust",
    } == CORE_PUBLIC_COMMANDS
    help_text = build_parser().format_help()
    for name in ("check", "lock", "ci", "gate", "diff", "why", "demo", "init", "status", "trust"):
        assert name in help_text
    listed = [
        line.strip()
        for line in help_text.splitlines()
        if line.startswith("    ") and not line.strip().startswith("(")
    ]
    assert not any(line.startswith("scan") for line in listed)
    assert not any(line.startswith("vet") for line in listed)
    assert not any(line.startswith("watch") for line in listed)
    assert not any(line.startswith("allow") for line in listed)
    assert not any(line.startswith("hook") for line in listed)
    # Review / advanced stay omitted from brief help.
    assert "Propose least-privilege" not in help_text
    assert "Explain a finding" not in help_text


def test_demo_target_resolves_packaged_fixture():
    target = _demo_target()
    assert target is not None
    assert target.is_dir()
    assert (target / "skills" / "bootstrap" / "SKILL.md").is_file()
    assert (target / ".cursor" / "mcp.json").is_file()


def test_demo_command_runs(tmp_path: Path):
    code = main(["demo", "-o", str(tmp_path / "out")])
    assert code == 0
    # Lock-only demo: PR comment + JSON delta; no research findings.json.
    assert (tmp_path / "out" / "pr-comment.md").is_file()
    assert (tmp_path / "out" / "authority-lock-delta.json").is_file()
    comment = (tmp_path / "out" / "pr-comment.md").read_text(encoding="utf-8")
    assert "Authority Diff" in comment
    assert "GROWTH" in comment or "NEEDS_REVIEW" in comment


def test_addition_class_and_empty_approvals(tmp_path: Path):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "npx", "args": ["-y", "pkg-a"]}}}),
        encoding="utf-8",
    )
    dest, lock = write_authority_lock(root, accept_gated=True)
    assert dest.is_file()
    assert "approvals" not in lock
    assert "approved_findings" not in lock

    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "a": {"command": "npx", "args": ["-y", "pkg-a"]},
                    "b": {"command": "npx", "args": ["-y", "pkg-b"]},
                }
            }
        ),
        encoding="utf-8",
    )
    head = build_authority_lock(root)
    delta = diff_authority_locks(lock, head)
    assert delta["summary"]["additions"] >= 1
    assert any(c.get("change_class") == "addition" for c in delta["changes"]["added"])

    code = main(["lock", str(root), "--accept-gated"])
    assert code == 0
    sealed = json.loads((root / "AUTHORITY.lock").read_text(encoding="utf-8"))
    assert "approvals" not in sealed
    assert "approved_findings" not in sealed
    assert sealed.get("lock_hash")


def test_agent_cannot_mutate_lock(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setenv("AUCTELIS_AGENT", "1")
    code = main(["lock", str(root)])
    assert code == 2
    assert not (root / "AUTHORITY.lock").exists()


def test_authority_not_established_vs_no_new():
    sparse = {
        "component_counts_by_maturity": {
            "SUPPORTED": 1,
            "PARTIAL": 4,
            "MANUAL_ONLY": 1,
            "UNSUPPORTED": 0,
        },
        "unparsed_agent_config_count": 0,
    }
    assert (
        authority_establishment(coverage=sparse, decision="NO-GATED-FINDINGS")
        == "AUTHORITY_NOT_ESTABLISHED"
    )
    solid = {
        "component_counts_by_maturity": {
            "SUPPORTED": 4,
            "PARTIAL": 0,
            "MANUAL_ONLY": 0,
            "UNSUPPORTED": 0,
        }
    }
    assert (
        authority_establishment(coverage=solid, decision="NO-GATED-FINDINGS") == "NO_NEW_AUTHORITY"
    )


def test_relationships_emitted_for_demo(tmp_path: Path):
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"
    scan, _payload, _code = run_scan(demo, output_dir=tmp_path / "out", fail_on="never")
    assert scan.relationships is not None
    doc = scan.to_findings_doc()
    assert "relationships" in doc
    # Synthetic pairing also works without a full scan.
    rels = emit_relationships(
        [
            {
                "component_id": "C-1",
                "host": "cursor",
                "kind": "Skill",
            },
            {
                "component_id": "C-2",
                "host": "cursor",
                "kind": "MCP Server Registration",
            },
        ]
    )
    assert any(r.kind == "skill_invokes_mcp" for r in rels)


def test_suppression_requires_owner_and_expires(tmp_path: Path):
    from auctelis.policy import load_policy

    path = tmp_path / ".auctelis.yml"
    path.write_text(
        """
version: 1
policy:
  mode: advisory
  ignore:
    - rule: AUCTELIS-RULE-002
      path: "**"
      justification: "missing owner and expiry"
""",
        encoding="utf-8",
    )
    try:
        load_policy(path)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "owner" in str(exc).lower() or "expires" in str(exc).lower()


def test_decision_still_computes_for_demo(tmp_path: Path):
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"
    scan, payload, _code = run_scan(demo, output_dir=tmp_path / "out", fail_on="never")
    decision = compute_decision(scan.findings, coverage=scan.coverage)
    assert decision in {"BLOCK", "REVIEW", "NO-GATED-FINDINGS"}
    comment = (payload.get("pr_comment") or "") + ""
    assert "Authority delta:" in comment or "Decision:" in comment


def test_gate_writes_pr_comment_without_findings(tmp_path: Path, monkeypatch):
    """Default Action path: sticky comment from gate delta, no findings.json."""
    from auctelis.export.pr_comment import AUCTELIS_COMMENT_MARKER, render_gate_pr_comment
    from auctelis.gate import run_gate

    root = tmp_path / "repo"
    root.mkdir()
    (root / "CODEOWNERS").write_text("AUTHORITY.lock @sec\n", encoding="utf-8")
    cursor = root / ".cursor"
    cursor.mkdir()
    (cursor / "mcp.json").write_text(
        json.dumps({"mcpServers": {"ok": {"command": "node", "args": ["ok.js"]}}}),
        encoding="utf-8",
    )
    assert main(["lock", str(root), "--accept-gated"]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    (cursor / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "ok": {"command": "node", "args": ["ok.js"]},
                    "evil": {"url": "https://evil.example/sse"},
                }
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    monkeypatch.setenv("AUCTELIS_OUTPUT_DIR", str(out))
    code = main(
        [
            "gate",
            str(root),
            "--base-lock",
            str(base),
            "--skip-ruleset-check",
            "--trust-head-codeowners",
        ]
    )
    assert code == 1
    assert not (out / "findings.json").is_file()
    comment_path = out / "pr-comment.md"
    assert comment_path.is_file()
    body = comment_path.read_text(encoding="utf-8")
    assert AUCTELIS_COMMENT_MARKER in body
    assert "Authority Diff" in body
    assert "GROWTH" in body or "NEEDS_REVIEW" in body
    report, _ = run_gate(root, base_lock=base, check_ruleset=False, trust_head_codeowners=True)
    rendered = render_gate_pr_comment(report)
    assert AUCTELIS_COMMENT_MARKER in rendered


def test_action_posts_comment_without_research_annotate():
    action = (
        Path(__file__).resolve().parents[1] / ".github" / "actions" / "auctelis-gate" / "action.yml"
    )
    text = action.read_text(encoding="utf-8")
    assert "name: Authority Diff PR comment" in text
    block = text.split("name: Authority Diff PR comment", 1)[1].split("\n    - name:", 1)[0]
    assert "annotate" not in block
    assert "auctelis-dev" not in text
    assert "github.event_name == 'pull_request'" in block
    template = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "auctelis"
        / "templates"
        / "auctelis-gate.yml"
    )
    assert "annotate" not in template.read_text(encoding="utf-8")


def test_status_check_comment_only_ok_without_ruleset(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert main(["init", str(root), "--owner", "sec", "--force"]) == 0
    assert main(["status", "--check", str(root)]) == 0


def test_status_check_enforce_offline_says_verify_not_false_failure(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert main(["init", str(root), "--owner", "sec", "--enforce", "--force"]) == 0
    # Offline, a correct enforce install is armed locally; ruleset verification
    # is a GitHub-side step, not a false local failure.
    assert main(["status", "--check", str(root)]) == 0
    # CI can still demand a verified ruleset explicitly.
    assert main(["status", "--check", "--require-protection", str(root)]) == 1
