from __future__ import annotations

from pathlib import Path

DEFAULT_OUTPUT_DIR_NAME = "authdiff-out"


def repo_root() -> Path:
    """Return the monorepo root when running from a git checkout.

    Installed wheels do not ship the monorepo layout. Callers that need
    checkout-only assets (schemas, corpus, prompts) must handle ``None`` /
    missing paths — never assume this resolves under site-packages.
    """
    return Path(__file__).resolve().parents[2]


def canonical_schema_path() -> Path:
    return repo_root() / "canonical" / "schemas" / "audit-report.schema.json"


def published_schema_paths() -> tuple[Path, ...]:
    """Published audit-report schema path(s) under ``schemas/``."""
    root = repo_root() / "schemas"
    return (root / "audit-report.schema.json",)


def versions_path() -> Path:
    """Prefer checkout canonical versions; fall back to packaged copy."""
    checkout = repo_root() / "canonical" / "versions.json"
    if checkout.is_file():
        return checkout
    packaged = Path(__file__).resolve().parent / "data" / "versions.json"
    return packaged


def version_file_path() -> Path:
    """Prefer checkout VERSION; fall back to packaged copy."""
    checkout = repo_root() / "VERSION"
    if checkout.is_file():
        return checkout
    return Path(__file__).resolve().parent / "data" / "VERSION"


def resolve_default_output_dir() -> Path:
    """Default artifact directory: cwd ``authdiff-out``, never under the scan target.

    Writing into the target tree pollutes later inventories and contradicts the
    passive / read-only assessment model when scanning an external repository.
    """
    return (Path.cwd() / DEFAULT_OUTPUT_DIR_NAME).resolve()
