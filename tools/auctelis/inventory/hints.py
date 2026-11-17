"""Shared static-analysis hint helpers for inventory adapters.

Keep token lists here so MCP / hooks / skills / Claude settings stay aligned.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

DOWNLOAD_EXEC_RE = re.compile(
    r"(curl\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"wget\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"iwr\s+[^\n|;]*\|\s*iex|invoke-webrequest[^\n|;]*\|\s*iex)",
    re.IGNORECASE,
)

_BARE_HOST_RE = re.compile(
    r"(?i)(?:curl|wget)\s+(?:-[^\s]+\s+)*(?:https?://)?([a-z0-9][a-z0-9.-]+\.[a-z]{2,})"
)

PERMISSION_BYPASS_RE = re.compile(
    r"(--dangerously-skip-permissions|--yolo\b|bypasspermissions|"
    r"permissionmode\s*[:=]\s*bypass|auto[_-]?approve\s*[:=]\s*true|"
    r"skip[_-]?permissions)",
    re.IGNORECASE,
)

_LIFECYCLE_TOKENS = (
    "before",
    "pretool",
    "pre-tool",
    "sessionstart",
    "sessionend",
    "posttool",
    "pretooluse",
    "posttooluse",
)


def download_and_execute_hint(text: str) -> str | None:
    """True only for pipe-to-shell download patterns — not bare ``curl`` mentions."""
    if DOWNLOAD_EXEC_RE.search(text or ""):
        return "download_and_execute"
    return None


def extract_url_hosts_from_command(text: str) -> list[str]:
    """Pull destination hosts out of ``curl|sh`` / ``wget|sh`` / URL shell strings."""
    out: list[str] = []
    blob = str(text or "")
    if not blob.strip():
        return out

    def _add(host: str) -> None:
        host = str(host or "").strip().lower().rstrip(".")
        if host and host not in out and "." in host:
            out.append(host)

    for match in re.finditer(r"(?i)(?:https?|wss?)://[^\s'\"\\|;]+", blob):
        try:
            host = urlparse(match.group(0)).hostname or ""
        except ValueError:
            host = ""
        _add(host)
    for match in _BARE_HOST_RE.finditer(blob):
        _add(match.group(1))
    return out


def permission_bypass_hint(text: str) -> str | None:
    if PERMISSION_BYPASS_RE.search(text):
        return "permission_bypass_flag"
    return None


def pre_execution_lifecycle_hint(text: str) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in ("before", "pretool", "pre-tool", "sessionstart")):
        return "pre_execution_lifecycle"
    return None


def hook_lifecycle_event_hint(text: str) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in _LIFECYCLE_TOKENS):
        return "hook_lifecycle_event"
    return None


def execution_boundary_hint(text: str) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in ("command", "shell", "exec", "subprocess")):
        return "possible_execution_boundary"
    return None
