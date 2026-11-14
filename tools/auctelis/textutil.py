"""Neutral text helpers shared by the rule engine and export renderers."""

from __future__ import annotations

import re

# Escape markdown specials that enable injection. Dots are left alone so paths
# like `.cursor/mcp.json` stay readable (ordered-list dots only matter at BOL).
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|>])")
_URL_RE = re.compile(r"https?://([^/\s]+)(\S*)", re.IGNORECASE)
_MENTION_RE = re.compile(r"(^|[^/\w])@[\w-]+")


def escape_markdown(value: str, *, max_len: int = 160) -> str:
    """Neutralize markdown/HTML injection from target-controlled strings."""
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    # Strip terminal/OSC control sequences as well as markdown.
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07", "", text)
    # Keep destination hosts visible in code spans; drop URL paths (injection defense).
    # Placeholders survive markdown escaping, then expand to unescaped `` `host` ``.
    hosts: list[str] = []

    def _stash_host(match: re.Match[str]) -> str:
        host = match.group(1) or "redacted-host"
        # Hostnames are shown inside code spans; strip only injection-prone chars.
        safe = re.sub(r"[\\`*_{}\[\]()#!|>]", "", host)
        hosts.append(safe or "redacted-host")
        return f"\x00HOST{len(hosts) - 1}\x00"

    text = _URL_RE.sub(_stash_host, text)
    text = _MENTION_RE.sub(r"\1[@]", text)
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = _MD_SPECIAL.sub(r"\\\1", text)
    for idx, host in enumerate(hosts):
        text = text.replace(f"\x00HOST{idx}\x00", f"`{host}`")
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text
