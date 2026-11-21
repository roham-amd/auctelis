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
    assert docker == '"image": "demo/img@sha256:<digest>"'


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
