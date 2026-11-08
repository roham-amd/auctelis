"""Shared child-process environment scrubbing for opt-in execute paths.

Used by ``authdiff run`` (broker) and ``authdiff snapshot --execute``.
Passive scans never call this module.
"""

from __future__ import annotations

import os
import re

_SECRETISH = re.compile(
    r"(api[_-]?key|token|secret|password|passwd|authorization|credential|private[_-]?key|"
    r"aws_|github_|openai_|anthropic_|npm_|pypi_)",
    re.IGNORECASE,
)

# Minimal host plumbing so innocuous local binaries still start.
_KEEP = frozenset(
    {
        "PATH",
        "PATHEXT",
        "SystemRoot",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "USERNAME",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TERM",
        "COLORTERM",
        "NO_COLOR",
        "FORCE_COLOR",
    }
)


def scrub_env(
    base: dict[str, str] | None = None,
    *,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return a least-privilege environment for a brokered child process.

    Drops secret-shaped keys and most unrelated variables. Does **not** sandbox
    network or filesystem — callers must document that limit.
    """
    src = base if base is not None else dict(os.environ)
    out: dict[str, str] = {}
    for key, value in src.items():
        if key in _KEEP and not _SECRETISH.search(key):
            out[key] = value
    out["AUTHDIFF_SCRUBBED_ENV"] = "1"
    if extra:
        out.update(extra)
    return out
