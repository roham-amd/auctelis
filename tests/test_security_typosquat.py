"""Unit tests for auctelis.security.typosquat (AUCT-062 / RULE-020)."""

from __future__ import annotations

from auctelis.security.typosquat import (
    load_known_names,
    nearest_typosquat,
    normalize_component_name,
)


def test_normalize_strips_version_suffix() -> None:
    assert normalize_component_name("lodash@4.17.21") == "lodash"
    assert normalize_component_name("@scope/pkg@1.0.0").startswith("@scope/")


def test_known_names_packaged() -> None:
    names = load_known_names()
    assert names
    assert all(isinstance(n, str) and n for n in names)


def test_nearest_typosquat_finds_close_name() -> None:
    known = load_known_names()
    # Prefer a real known name so the distance check is meaningful.
    base = next((n for n in known if len(n) >= 5 and not n.startswith("@")), None)
    if base is None:
        base = known[0]
    # Single-character edit that stays within max_distance=2.
    candidate = base[:-1] + ("z" if base[-1] != "z" else "y")
    hit = nearest_typosquat(candidate, max_distance=2)
    assert hit is not None
    assert hit["known"] == base
    assert 1 <= int(hit["distance"]) <= 2


def test_exact_known_name_is_not_typosquat() -> None:
    known = load_known_names()
    assert nearest_typosquat(known[0]) is None


def test_short_names_ignored() -> None:
    assert nearest_typosquat("ab") is None
