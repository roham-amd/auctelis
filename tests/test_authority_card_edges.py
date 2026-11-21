"""Authority-card edge cases (Windows launchers, overflow summaries)."""

from __future__ import annotations

from auctelis.authority_card import (
    delta_cards,
    launcher,
    pin_config_snippet,
    pin_suggestion,
    record_card,
)
from auctelis.reach_tiers import TIER_FAIL, record_reach_tier


def test_launcher_extracts_windows_basename():
    assert launcher({"launcher": r"C:\Python\Scripts\npx.exe"}) == "npx.exe"
    assert launcher({"launcher": "/usr/local/bin/uvx"}) == "uvx"
    assert launcher({"launcher": "npx"}) == "npx"
    assert launcher({}) == ""


def test_record_card_shows_windows_launcher_basename():
    record = {
        "kind": "MCP Server Registration",
        "name": "win",
        "launcher": r"C:\Tools\npm\npx.cmd",
        "pin_state": "floating",
        "evidence_strength": "LITERAL_CONFIG",
    }
    card = record_card(record)
    assert "launcher npx.cmd" in card
    assert r"C:\Tools" not in card
    assert record_reach_tier(record) == TIER_FAIL


def test_delta_cards_overflow_summary_names_hidden_records():
    delta = {
        "summary": {
            "additions": 3,
            "expansions": 0,
            "reductions": 0,
            "replacements": 0,
            "policy_changed": False,
            "meaningful_authority_change": True,
            "max_reach_tier": 2,
        },
        "changes": {
            "added": [
                {
                    "kind": "MCP Server Registration",
                    "name": f"srv{i}",
                    "path": ".cursor/mcp.json",
                    "capabilities": ["access_secrets"],
                    "env_keys": ["TOKEN"],
                    "evidence_strength": "LITERAL_CONFIG",
                    "pin_state": "floating",
                }
                for i in range(3)
            ],
            "removed": [],
            "changed": [],
        },
    }
    cards = delta_cards(delta, limit=1, include_overflow_summary=True)
    assert len(cards) == 2
    assert cards[-1].startswith("+2 more:")
    assert "srv2" in cards[-1] or "srv1" in cards[-1]


def test_pin_suggestion_docker_uses_digest():
    suggestion = pin_suggestion({"launcher": "docker", "pin_state": "floating"})
    assert "sha256" in suggestion


def test_pin_suggestion_names_concrete_package_from_args():
    suggestion = pin_suggestion(
        {
            "launcher": "npx",
            "pin_state": "floating",
            "args": ["-y", "demo-evil-mcp"],
        }
    )
    assert "demo-evil-mcp@<exact-version>" in suggestion
    assert "<pkg>" not in suggestion


def test_pin_config_snippet_for_npx_uvx_docker():
    npx = pin_config_snippet(
        {"launcher": "npx", "pin_state": "floating", "args": ["-y", "demo-evil-mcp"]}
    )
    assert npx == '"args": ["-y", "demo-evil-mcp@<exact-version>"]'
    uvx = pin_config_snippet({"launcher": "uvx", "pin_state": "floating", "args": ["demo-tool"]})
    assert uvx == '"args": ["demo-tool==<exact-version>"]'
    docker = pin_config_snippet(
        {"launcher": "docker", "pin_state": "floating", "args": ["run", "demo/img"]}
    )
    assert docker == '"args": ["run", "demo/img@sha256:<digest>"]'
    assert '"image"' not in docker


def test_auct038_package_stem_fallback_without_args():
    """AUCT-038: lock-only records with package_stem still produce pin snippets."""
    snippet = pin_config_snippet(
        {
            "kind": "MCP Server Registration",
            "launcher": "npx",
            "pin_state": "floating",
            "package_stem": "@linear/mcp",
        }
    )
    assert snippet == '"args": ["-y", "@linear/mcp@<exact-version>"]'


def test_pin_tightening_card_shows_unpinned_to_pinned():
    """AUCT-029: reviewers see pin: unpinned → pinned on the reduction card."""
    delta = {
        "summary": {
            "additions": 0,
            "expansions": 0,
            "reductions": 1,
            "replacements": 0,
            "policy_changed": False,
            "meaningful_authority_change": True,
            "max_reach_tier": 0,
        },
        "changes": {
            "added": [],
            "removed": [],
            "changed": [
                {
                    "change_class": "reduction",
                    "before": {
                        "kind": "MCP Server Registration",
                        "name": "demo",
                        "path": ".cursor/mcp.json",
                        "launcher": "npx",
                        "pin_state": "floating",
                        "capabilities": ["invoke_tools"],
                        "evidence_strength": "LITERAL_CONFIG",
                    },
                    "after": {
                        "kind": "MCP Server Registration",
                        "name": "demo",
                        "path": ".cursor/mcp.json",
                        "launcher": "npx",
                        "pin_state": "pinned",
                        "capabilities": ["invoke_tools"],
                        "evidence_strength": "LITERAL_CONFIG",
                    },
                }
            ],
        },
    }
    cards = delta_cards(delta, limit=5)
    assert cards
    assert any("pin: unpinned → pinned" in c for c in cards)
    assert any(c.startswith("~") for c in cards)


def test_auct043_pin_snippet_preserves_args_and_strips_floating_tags():
    """AUCT-043: pasteable pins keep argv, drop @latest/:latest, and stay valid JSON."""
    import json

    preserved = pin_config_snippet(
        {
            "launcher": "npx",
            "pin_state": "floating",
            "args": ["-y", "@scope/mcp", "/workspace"],
        }
    )
    assert preserved == '"args": ["-y", "@scope/mcp@<exact-version>", "/workspace"]'
    assert json.loads("{" + preserved + "}")["args"] == [
        "-y",
        "@scope/mcp@<exact-version>",
        "/workspace",
    ]

    floating = pin_config_snippet(
        {"launcher": "npx", "pin_state": "floating", "args": ["-y", "foo@latest"]}
    )
    assert floating == '"args": ["-y", "foo@<exact-version>"]'
    assert "foo@latest@" not in floating
    suggestion = pin_suggestion(
        {"launcher": "npx", "pin_state": "floating", "args": ["-y", "foo@latest"]}
    )
    assert "foo@latest@" not in suggestion
    assert "foo@<exact-version>" in suggestion

    docker = pin_config_snippet(
        {
            "launcher": "docker",
            "pin_state": "floating",
            "args": ["run", "-i", "--rm", "mcp/sqlite:latest"],
        }
    )
    assert '"image"' not in docker
    assert json.loads("{" + docker + "}")["args"] == [
        "run",
        "-i",
        "--rm",
        "mcp/sqlite@sha256:<digest>",
    ]
    stem_only = pin_config_snippet(
        {"launcher": "podman", "pin_state": "floating", "package_stem": "mcp/sqlite"}
    )
    assert '"image"' not in stem_only
    assert json.loads("{" + stem_only + "}")["args"] == [
        "run",
        "...",
        "mcp/sqlite@sha256:<digest>",
    ]
    assert pin_config_snippet({"launcher": "docker", "pin_state": "floating"}) == ""


def test_auct043_over_budget_preserved_args_are_omitted_not_truncated():
    from auctelis.export.pr_comment import render_gate_pr_comment
    from auctelis.textutil import PASTEABLE_SNIPPET_MAX, markdown_code_span

    extra = "w" * 90
    record = {
        "kind": "MCP Server Registration",
        "name": "srv",
        "path": ".cursor/mcp.json",
        "launcher": "npx",
        "pin_state": "floating",
        "args": ["-y", "@scope/mcp", "/" + extra],
        "capabilities": ["invoke_tools"],
        "evidence_strength": "LITERAL_CONFIG",
    }
    snippet = pin_config_snippet(record)
    assert extra in snippet
    assert len(snippet) > PASTEABLE_SNIPPET_MAX
    assert "…" not in snippet
    assert markdown_code_span(snippet) is None
    report = {
        "verdict": "NEEDS_REVIEW",
        "mode": "comment-only",
        "required_owners": ["@security"],
        "unparsed": 0,
        "coverage": {},
        "delta": {
            "summary": {
                "additions": 1,
                "expansions": 0,
                "reductions": 0,
                "meaningful_authority_change": True,
                "max_reach_tier": 2,
            },
            "changes": {"added": [record], "changed": [], "removed": []},
            "lines": ['+ mcp "srv"'],
        },
    }
    body = render_gate_pr_comment(report)
    assert "**Pin fix:**" not in body
    assert extra not in body
    assert "…" not in body
