"""Detect env keys that redirect model/API traffic or proxies."""

from __future__ import annotations

import re

_ROUTING_OVERRIDE_KEY_RE = re.compile(
    r"^(?:API_BASE_URL|.+_BASE_URL|HTTPS_PROXY|HTTP_PROXY|ALL_PROXY)$",
    re.IGNORECASE,
)

_STATIC_OVERRIDES = frozenset(
    {
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_URL",
        "OPENAI_BASE_URL",
    }
)


def is_routing_override_env_key(key: str) -> bool:
    upper = str(key).upper()
    if upper in _STATIC_OVERRIDES:
        return True
    return bool(_ROUTING_OVERRIDE_KEY_RE.match(upper))
