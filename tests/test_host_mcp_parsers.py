"""Week 3: project-level MCP host config parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from authdiff.inventory.collector import collect_inventory

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "hosts"


@pytest.mark.parametrize(
    ("fixture", "expected_host"),
    [
        ("gemini-mcp", "gemini"),
        ("zed-mcp", "zed"),
        ("opencode-mcp", "opencode"),
        ("codex-mcp", "codex"),
        ("continue-mcp", "continue"),
        ("claude-user-mcp", "claude-code"),
    ],
)
def test_host_mcp_fixture_yields_registration(fixture: str, expected_host: str):
    root = _FIXTURES / fixture
    inv = collect_inventory(root)
    regs = [c for c in inv.components if c.get("type") == "MCP Server Registration"]
    assert len(regs) >= 1, inv.parser_events
    assert any((c.get("host_id") or "") == expected_host for c in regs), regs
