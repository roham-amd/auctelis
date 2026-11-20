"""Shared watched-path predicate for Action path_filter and GitHub audits.

Keep this list aligned with ``action.yml`` path_filter and
``tests/test_action_path_filter.py``. Agent-config and protection paths only —
plain application source must never match.
"""

from __future__ import annotations

import re

# Grep -iE pattern embedded in action.yml path_filter (single source for tests).
PATH_FILTER_GREP = (
    r"(^|/)(\.cursor|\.claude|\.codex|\.gemini|\.vscode|\.zed|\.config/zed|\.continue|"
    r"\.kiro|\.roo|\.amazonq|\.opencode|\.windsurf|windsurf|"
    r"\.github/workflows|\.github/actions|\.github/instructions|\.auctelis|\.clinerules)/|"
    r"(^|/)(\.github/CODEOWNERS|\.github/copilot-instructions\.md|\.mcp\.json|\.claude\.json|"
    r"opencode\.json|mcp[^/]*\.json|[^/]*mcp[^/]*\.toml|codex\.toml|SKILL\.md|AGENTS\.md|"
    r"CLAUDE\.md|GEMINI\.md|\.gemini\.md|CODEX\.md|\.cursorrules|\.windsurfrules|"
    r"windsurfrules|\.clinerules|copilot-instructions\.md|hooks\.(json|ya?ml)|"
    r"hooks/[^/]+\.(json|md|py)|plugin\.(json|ya?ml)|\.cursor-plugin|"
    r"[^/]*plugin[^/]*/package\.json|(sub)?agents\.json|(sub)?agents/[^/]+\.(md|json|ya?ml)|"
    r"automations?\.json|automation\.ya?ml|automations/[^/]+\.(json|ya?ml|md)|"
    r"agent[-_]card\.json|AUTHORITY\.lock|\.auctelis\.yml|CODEOWNERS)$"
)

_PATH_FILTER_RE = re.compile(PATH_FILTER_GREP, re.IGNORECASE)

# Cap blob fetches per repo for zero-clone audits (AUCT-022).
MAX_WATCHED_FILES_PER_REPO = 100
DEFAULT_MAX_FILE_BYTES = 512_000


def is_watched_path(rel: str) -> bool:
    """True when ``rel`` (repo-relative, forward slashes) is an agent-config path."""
    text = str(rel or "").replace("\\", "/")
    # Do not use str.lstrip("./") — that strips any leading '.' and breaks
    # ``.cursor/`` / ``.github/`` paths into ``cursor/`` / ``github/``.
    while text.startswith("./"):
        text = text[2:]
    if not text or text.startswith("/") or ".." in text.split("/"):
        return False
    return bool(_PATH_FILTER_RE.search(text))
