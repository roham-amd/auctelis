"""Package-name normalization shared by build gates and deps helpers."""

from __future__ import annotations


def normalize_package_name(name: str) -> str:
    """PEP 503-ish normalization: lowercase with underscores as hyphens."""
    return name.replace("_", "-").lower()
