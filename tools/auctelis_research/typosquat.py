"""Re-exports typosquat helpers from the product security package."""

from __future__ import annotations

from auctelis.security.typosquat import (
    load_known_names,
    nearest_typosquat,
    normalize_component_name,
)

__all__ = [
    "load_known_names",
    "nearest_typosquat",
    "normalize_component_name",
]
