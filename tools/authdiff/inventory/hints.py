"""Shared static-analysis hint helpers for inventory adapters.

Keep token lists here so MCP / hooks / skills / Claude settings stay aligned.
"""

from __future__ import annotations

import re

DOWNLOAD_EXEC_RE = re.compile(
    r"(curl\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"wget\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"iwr\s+[^\n|;]*\|\s*iex|invoke-webrequest[^\n|;]*\|\s*iex)",
    re.IGNORECASE,
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
    if DOWNLOAD_EXEC_RE.search(text) or any(
        token in text.lower() for token in ("curl ", "wget ", "invoke-webrequest", "| sh", "| bash")
    ):
        return "download_and_execute"
    return None


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
