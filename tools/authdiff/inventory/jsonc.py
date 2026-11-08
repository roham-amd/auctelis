"""Tolerant JSON / JSONC loading for host MCP configs.

VS Code and some Cursor configs allow ``//`` comments and trailing commas.
Strict ``json.loads`` previously recorded a parse_error and dropped the file,
which attackers can use to hide MCP registrations.
"""

from __future__ import annotations

import json
import re
from typing import Any

_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def strip_jsonc(text: str) -> str:
    """Best-effort strip of // and /* */ comments plus trailing commas."""
    # Protect string contents by a coarse pass: remove comments outside quotes.
    out: list[str] = []
    i = 0
    n = len(text)
    in_str = False
    escape = False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            continue
        out.append(ch)
        i += 1
    stripped = "".join(out)
    return _TRAILING_COMMA_RE.sub(r"\1", stripped)


def loads_json_tolerant(text: str) -> Any:
    """Parse JSON, falling back to JSONC stripping once."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(strip_jsonc(text))
