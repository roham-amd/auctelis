"""Typosquat distance helpers for AUTHDIFF-RULE-020 (known-name proximity)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def normalize_component_name(raw: str) -> str:
    name = str(raw or "").strip().lower()
    # Compare bare package identity: drop scope and trailing version tags.
    if name.startswith("@"):
        # @scope/pkg → keep full scoped form for exact known-list match
        pass
    if "@" in name and not name.startswith("@"):
        name = name.split("@", 1)[0]
    return name.strip()


@lru_cache(maxsize=1)
def load_known_names() -> tuple[str, ...]:
    path = Path(__file__).resolve().parent / "data" / "known-component-names.json"
    if not path.is_file():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    names = [normalize_component_name(n) for n in (data.get("names") or [])]
    return tuple(sorted({n for n in names if n}))


def nearest_typosquat(
    candidate: str,
    *,
    max_distance: int = 2,
) -> dict[str, Any] | None:
    """Return closest known name within ``max_distance``, excluding exact matches."""
    name = normalize_component_name(candidate)
    if not name or len(name) < 3:
        return None
    best: tuple[int, str] | None = None
    for known in load_known_names():
        if name == known:
            return None
        # Avoid flagging unrelated short collisions (e.g. "aws" vs "as").
        if abs(len(name) - len(known)) > max_distance:
            continue
        dist = _levenshtein(name, known)
        if dist == 0 or dist > max_distance:
            continue
        if best is None or dist < best[0]:
            best = (dist, known)
    if best is None:
        return None
    return {"candidate": name, "known": best[1], "distance": best[0]}
