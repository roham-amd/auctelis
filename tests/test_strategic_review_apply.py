"""Regression coverage for strategic review application (auctelis north-star)."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import build_authority_lock, diff_authority_locks, write_authority_lock
from auctelis.cli import main
from auctelis.cli.dispatch import _demo_target
from auctelis.cli.parser import CORE_PUBLIC_COMMANDS, build_parser
from auctelis.security.decision import authority_establishment, compute_decision
from auctelis.security.relationships import emit_relationships
from auctelis.security.scan import run_scan


def test_core_public_commands_are_six_jobs():
    # check remains a scan alias; open/init-gate aliases were removed.
    assert {
        "demo",
        "doctor",
        "vet",
        "scan",
        "check",
        "lock",
        "gate",
        "ci",
    } == CORE_PUBLIC_COMMANDS
    help_text = build_parser().format_help()
    for name in ("demo", "doctor", "vet", "scan", "lock", "gate", "ci"):
        assert name in help_text
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
    assert (tmp_path / "out" / "findings.json").is_file()
    assert (tmp_path / "out" / "pr-comment.md").is_file()


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
    assert lock.get("approvals") == []

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

    code = main(["lock", str(root), "--approval", "@security-owners", "--accept-gated"])
    assert code == 0
    sealed = json.loads((root / "AUTHORITY.lock").read_text(encoding="utf-8"))
    assert sealed.get("approvals") in ([], None)
    assert sealed.get("approved_findings") or sealed.get("lock_hash")


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
