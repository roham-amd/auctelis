"""Edge cases for reach tiering and trusted-destination handling."""

from __future__ import annotations

from auctelis.reach_tiers import (
    TIER_COMMENT,
    TIER_FAIL,
    TIER_SILENT,
    delta_max_reach_tier,
    expansion_reach_tier,
    reach_reason,
    record_reach_tier,
    valid_trusted_host,
)


def test_instructions_only_record_is_silent():
    record = {
        "kind": "Rule / instruction file",
        "capabilities": ["modify_agent_instructions"],
        "destinations": [],
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert record_reach_tier(record) == TIER_SILENT
    assert reach_reason(record) == "instructions"


def test_unknown_capability_defaults_to_comment():
    unknown = {
        "kind": "Plugin",
        "capabilities": ["synthetic_future_capability"],
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert record_reach_tier(unknown) == TIER_COMMENT
    tools = {
        "kind": "Plugin",
        "capabilities": ["invoke_tools"],
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert reach_reason(tools) == "tools"


def test_posture_and_capability_reasons():
    assert (
        reach_reason(
            {
                "kind": "Host Settings",
                "approval_posture": "bypass",
                "capabilities": [],
                "evidence_strength": "LITERAL_CONFIG",
            }
        )
        == "bypass permissions"
    )
    assert reach_reason({"capabilities": ["execute"], "evidence_strength": "LITERAL_CONFIG"}) == (
        "execute"
    )
    assert (
        reach_reason({"capabilities": ["modify_approvals"], "evidence_strength": "LITERAL_CONFIG"})
        == "approvals"
    )
    assert (
        reach_reason(
            {"capabilities": ["unattended_operation"], "evidence_strength": "LITERAL_CONFIG"}
        )
        == "unattended"
    )
    assert (
        reach_reason({"kind": "Hook", "capabilities": [], "evidence_strength": "LITERAL_CONFIG"})
        == "new authority"
    )
    assert (
        reach_reason(
            {
                "kind": "Plugin",
                "launcher": "npx",
                "pin_state": "floating",
                "capabilities": ["access_network"],
                "evidence_strength": "LITERAL_CONFIG",
            }
        )
        == "unpinned launcher"
    )
    assert (
        reach_reason(
            {
                "capabilities": ["access_network"],
                "destinations": ["api.example.com"],
                "evidence_strength": "LITERAL_CONFIG",
            },
            trusted_hosts={"api.example.com"},
        )
        == "trusted destination"
    )
    assert reach_reason({"capabilities": [], "evidence_strength": "LITERAL_CONFIG"}) == (
        "recorded authority"
    )


def test_trusted_destination_lowers_network_only():
    record = {
        "kind": "MCP Server Registration",
        "capabilities": ["access_network"],
        "destinations": ["mcp.linear.app"],
        "evidence_strength": "LITERAL_CONFIG",
    }
    # A URL-only MCP registration is trusted down to the comment tier.
    assert record_reach_tier(record, trusted_hosts={"mcp.linear.app"}) == TIER_COMMENT
    # A trusted host never hides a launcher: the record is not network-only.
    unpinned = {**record, "launcher": "npx", "pin_state": "floating"}
    assert record_reach_tier(unpinned, trusted_hosts={"mcp.linear.app"}) >= TIER_FAIL
    pinned = {**record, "launcher": "npx", "pin_state": "pinned"}
    assert record_reach_tier(pinned, trusted_hosts={"mcp.linear.app"}) >= TIER_FAIL


def test_valid_trusted_host_rejects_suffix_wide_entries():
    assert valid_trusted_host("mcp.linear.app")
    assert valid_trusted_host("localhost")
    assert not valid_trusted_host("com")
    assert not valid_trusted_host("*.example.com")
    assert not valid_trusted_host(".example.com")
    assert not valid_trusted_host("")


def test_expansion_tier_rules():
    before = {
        "kind": "MCP Server Registration",
        "capabilities": ["access_network"],
        "destinations": ["a.example.com"],
        "env_keys": [],
    }
    literal_env = {
        **before,
        "env_keys": ["API_TOKEN"],
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert expansion_reach_tier(before, literal_env) >= TIER_FAIL

    trusted_dest = {
        **before,
        "destinations": ["a.example.com", "b.example.com"],
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert expansion_reach_tier(before, trusted_dest, trusted_hosts={"b.example.com"}) == (
        TIER_SILENT
    )

    inferred_instructions = {
        "kind": "Rule / instruction file",
        "capabilities": ["modify_agent_instructions", "access_network"],
        "destinations": ["docs.example.com"],
        "evidence_strength": "INFERRED_HINT",
    }
    assert expansion_reach_tier({}, inferred_instructions) == TIER_COMMENT


def test_delta_max_tier_tracks_mcp_tool_and_policy_changes():
    assert (
        delta_max_reach_tier(
            {
                "summary": {"policy_changed": False},
                "changes": {"added": [], "changed": [], "mcp_tools_added": ["read"]},
            }
        )
        == TIER_FAIL
    )
    assert (
        delta_max_reach_tier(
            {
                "summary": {"policy_changed": True},
                "changes": {"added": [], "changed": []},
            }
        )
        == TIER_FAIL
    )
    assert delta_max_reach_tier({"changes": {"added": [], "changed": []}}) == TIER_SILENT
    assert delta_max_reach_tier({}) == TIER_SILENT


def test_plain_ci_bare_plugin_and_execute_commands(tmp_path):
    from auctelis.security.authority import build_authority_snapshot
    from auctelis.security.engine import run_authority_inventory

    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "test.yml").write_text(
        "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pytest\n",
        encoding="utf-8",
    )
    (wf_dir / "agent.yml").write_text(
        "name: Agent\non: [pull_request]\njobs:\n  ai:\n    runs-on: ubuntu-latest\n    env:\n      API_KEY: ${{ secrets.API_KEY }}\n    steps:\n      - uses: anthropics/claude-code-action@v1\n",
        encoding="utf-8",
    )
    snap = build_authority_snapshot(run_authority_inventory(tmp_path))
    by_path = {c["path"]: c for c in snap["components"]}
    assert record_reach_tier(by_path[".github/workflows/test.yml"]) == TIER_SILENT
    assert record_reach_tier(by_path[".github/workflows/agent.yml"]) == TIER_FAIL

    bare_plugin = {
        "kind": "Plugin",
        "capabilities": [],
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert record_reach_tier(bare_plugin) <= TIER_COMMENT

    exec_cmd = {
        "kind": "Skill",
        "capabilities": ["execute_commands"],
        "evidence_strength": "LITERAL_CONFIG",
    }
    assert record_reach_tier(exec_cmd) == TIER_FAIL
    assert reach_reason(exec_cmd) == "execute"
