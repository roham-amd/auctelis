"""Regressions for the north-star apply: CODEOWNERS paths, tiers, tomllib, PASS text."""

from __future__ import annotations

from pathlib import Path

from auctelis.authority_lock import diff_authority_locks
from auctelis.cli import main
from auctelis.cli.dispatch import _merge_codeowners_authority, _rel_authority_path
from auctelis.gate import render_gate_report
from auctelis.reach_tiers import TIER_FAIL, TIER_SILENT, delta_max_reach_tier, record_reach_tier


def test_rel_authority_path_preserves_dotdirs():
    assert _rel_authority_path(".vscode/mcp.json") == ".vscode/mcp.json"
    assert _rel_authority_path("./.cursor/rules/x.mdc") == ".cursor/rules/x.mdc"
    assert _rel_authority_path(".github/workflows/ci.yml") == ".github/workflows/ci.yml"


def test_init_codeowners_covers_dot_directories(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".vscode").mkdir()
    (root / ".vscode" / "mcp.json").write_text(
        '{"mcpServers":{"demo":{"command":"npx","args":["-y","pkg"]}}}',
        encoding="utf-8",
    )
    (root / ".cursor").mkdir()
    (root / ".cursor" / "rules").mkdir()
    (root / ".cursor" / "rules" / "setup.mdc").write_text("# setup\n", encoding="utf-8")
    code = main(["init", str(root), "--owner", "security", "--force"])
    assert code == 0
    owners = (root / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert ".vscode/mcp.json" in owners
    # Must not write the broken stripped form from str.lstrip("./").
    assert not any(line.startswith("vscode/mcp.json ") for line in owners.splitlines())
    assert not any(line.startswith("cursor/rules/") for line in owners.splitlines())


def test_merge_codeowners_keeps_leading_dot():
    merged = _merge_codeowners_authority(
        "AUTHORITY.lock @sec\n",
        "@sec",
        extra_paths=[".vscode/mcp.json", "./.codex/config.toml"],
    )
    assert ".vscode/mcp.json @sec" in merged
    assert ".codex/config.toml @sec" in merged
    assert "vscode/mcp.json @sec" not in merged.replace(".vscode/mcp.json @sec", "")


def test_inferred_doc_link_is_not_fail_tier():
    before = {
        "kind": "Rule / instruction file",
        "capabilities": ["modify_agent_instructions"],
        "destinations": [],
        "evidence_strength": "INFERRED_HINT",
    }
    after = {
        "kind": "Rule / instruction file",
        "capabilities": ["modify_agent_instructions", "access_network"],
        "destinations": ["docs.python.org"],
        "evidence_strength": "INFERRED_HINT",
    }
    delta = {
        "summary": {"policy_changed": False},
        "changes": {
            "added": [],
            "changed": [
                {
                    "change_class": "expansion",
                    "before": before,
                    "after": after,
                }
            ],
            "mcp_tools_added": [],
            "mcp_tools_changed": [],
        },
    }
    assert delta_max_reach_tier(delta) < TIER_FAIL
    assert record_reach_tier(after) <= TIER_SILENT or delta_max_reach_tier(delta) < TIER_FAIL


def test_new_mcp_is_fail_tier():
    rec = {
        "kind": "MCP Server Registration",
        "capabilities": ["invoke_tools", "access_network"],
        "destinations": ["mcp.linear.app"],
        "launcher": "npx",
        "pin_state": "floating",
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert record_reach_tier(rec) >= TIER_FAIL


def test_diff_marks_doc_expansion_non_material():
    base = {
        "version": 1,
        "policy_hash": None,
        "records": [
            {
                "id": "agents",
                "identity_key": "agents|rule|agents",
                "kind": "Rule / instruction file",
                "name": "agents",
                "path": "AGENTS.md",
                "host": "generic",
                "capabilities": ["modify_agent_instructions"],
                "destinations": [],
                "env_keys": [],
                "permission_allows": [],
                "pin_state": "n/a",
                "approval_posture": "unknown",
                "launcher": "",
                "url_host": "",
                "args_digest": "",
                "script_digest": "",
                "digest": "sha256:a",
                "fingerprint": "a",
                "evidence_strength": "INFERRED_HINT",
                "capability_origin": "TYPE_DEFAULT",
            }
        ],
        "mcp_tools": {},
    }
    head = {
        "version": 1,
        "policy_hash": None,
        "records": [
            {
                **base["records"][0],
                "capabilities": ["modify_agent_instructions", "access_network"],
                "destinations": ["docs.python.org"],
            }
        ],
        "mcp_tools": {},
    }
    delta = diff_authority_locks(base, head)
    assert delta["summary"]["max_reach_tier"] < TIER_FAIL
    assert delta["summary"]["material_authority_change"] is False


def test_lockless_diff_template_exists():
    template = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "auctelis"
        / "templates"
        / "auctelis-diff.yml"
    )
    text = template.read_text(encoding="utf-8")
    assert 'locked: "false"' in text
    assert "auctelis-gate@" in text
    assert "pull_request" in text


def test_research_package_importable_from_source():
    import auctelis_research

    assert auctelis_research.__file__


def test_needs_review_error_drops_pass_prefix():
    text = render_gate_report(
        {
            "verdict": "NEEDS_REVIEW",
            "protection": "unverified",
            "label": "GROWTH",
            "needs_approval": True,
            "required_owners": ["@sec"],
            "ruleset": "UNVERIFIED",
            "ruleset_detail": "no token",
            "strict_ruleset": True,
            "lines": [],
            "error": ("1 agent config file(s) could not be parsed on head — review before merge."),
            "ok": False,
        }
    )
    assert "NEEDS_REVIEW" in text
    assert "PASS /" not in text
