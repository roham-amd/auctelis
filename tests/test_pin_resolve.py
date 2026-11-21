"""AUCT-050 — opt-in resolved Pin fix."""

from __future__ import annotations

from datetime import UTC, datetime

from auctelis.authority_card import pin_config_snippet, pin_report
from auctelis.pin_resolve import resolve_pin_item, resolve_pins_document


def _fetcher_map(mapping: dict[str, tuple[int, object]]):
    def fetcher(url: str):
        for key, value in mapping.items():
            if key in url:
                return value
        return 404, {"message": "not found"}

    return fetcher


def test_resolve_npx_and_uvx_with_injected_fetcher():
    now = datetime(2026, 11, 22, tzinfo=UTC)
    npx_item = {
        "name": "linear",
        "path": ".cursor/mcp.json",
        "launcher": "npx",
        "pin_state": "floating",
        "suggestion": "pin the package: npx -y @linear/mcp@<exact-version>",
        "config_snippet": pin_config_snippet(
            {"launcher": "npx", "pin_state": "floating", "args": ["-y", "@linear/mcp"]}
        ),
    }
    uvx_item = {
        "name": "demo",
        "path": ".mcp.json",
        "launcher": "uvx",
        "pin_state": "floating",
        "suggestion": "pin the package: demo-tool==<exact-version>",
        "config_snippet": pin_config_snippet(
            {"launcher": "uvx", "pin_state": "floating", "args": ["demo-tool"]}
        ),
    }
    docker_item = {
        "name": "img",
        "path": ".mcp.json",
        "launcher": "docker",
        "pin_state": "floating",
        "suggestion": "pin the image: demo@sha256:<digest>",
        "config_snippet": pin_config_snippet(
            {
                "launcher": "docker",
                "pin_state": "floating",
                "args": ["run", "--rm", "demo"],
            }
        ),
    }
    fetcher = _fetcher_map(
        {
            "registry.npmjs.org": (200, {"dist-tags": {"latest": "1.2.3"}}),
            "pypi.org": (200, {"info": {"version": "4.5.6"}}),
        }
    )
    assert resolve_pin_item(npx_item, fetcher=fetcher, now=now) is True
    assert npx_item["resolved_pin"] == "@linear/mcp@1.2.3"
    assert npx_item["resolved_at"] == "2026-11-22"
    assert "@linear/mcp@1.2.3" in npx_item["resolved_config_snippet"]
    assert "<exact-version>" in npx_item["config_snippet"]

    assert resolve_pin_item(uvx_item, fetcher=fetcher, now=now) is True
    assert uvx_item["resolved_pin"] == "demo-tool==4.5.6"

    assert resolve_pin_item(docker_item, fetcher=fetcher, now=now) is False
    assert "resolved_pin" not in docker_item


def test_resolve_timeout_or_404_keeps_placeholder():
    item = {
        "name": "x",
        "launcher": "npx",
        "config_snippet": '"args": ["-y", "demo@<exact-version>"]',
        "suggestion": "pin the package: npx -y demo@<exact-version>",
    }
    assert resolve_pin_item(item, fetcher=lambda _url: (404, None)) is False
    assert "resolved_pin" not in item
    assert resolve_pin_item(item, fetcher=lambda _url: (0, None)) is False


def test_pin_report_default_unchanged_without_resolve():
    records = [
        {
            "kind": "mcp",
            "name": "linear",
            "path": ".cursor/mcp.json",
            "launcher": "npx",
            "pin_state": "floating",
            "args": ["-y", "@linear/mcp"],
            "capabilities": ["access_network", "access_secrets"],
        }
    ]
    before = pin_report(records)
    after = pin_report(records)
    assert before == after
    assert all("resolved_pin" not in item for item in after["items"])
    resolve_pins_document(
        after,
        fetcher=_fetcher_map({"registry.npmjs.org": (200, {"dist-tags": {"latest": "9.9.9"}})}),
        now=datetime(2026, 11, 22, tzinfo=UTC),
    )
    assert after["items"][0]["resolved_pin"] == "@linear/mcp@9.9.9"
