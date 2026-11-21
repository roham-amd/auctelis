from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CollectorLimits:
    max_files: int = 50_000
    max_depth: int = 16
    max_file_bytes: int = 2_000_000


def _env_int(name: str, default: int) -> int:
    raw = str(os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def resolve_collector_limits(
    *,
    max_files: int | None = None,
    max_depth: int | None = None,
    max_file_bytes: int | None = None,
) -> CollectorLimits:
    """Build limits from explicit args, else ``AUCTELIS_MAX_*`` env, else defaults."""
    defaults = CollectorLimits()
    return CollectorLimits(
        max_files=(
            max(1, int(max_files))
            if max_files is not None
            else _env_int("AUCTELIS_MAX_FILES", defaults.max_files)
        ),
        max_depth=(
            max(1, int(max_depth))
            if max_depth is not None
            else _env_int("AUCTELIS_MAX_DEPTH", defaults.max_depth)
        ),
        max_file_bytes=(
            max(1, int(max_file_bytes)) if max_file_bytes is not None else defaults.max_file_bytes
        ),
    )
