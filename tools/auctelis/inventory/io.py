from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from auctelis.inventory.limits import CollectorLimits

_SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".venv-smoke",
    "__pycache__",
    ".tox",
    "dist",
    "build",
    # Exact name; prefix auctelis-out-* handled in the walk below
    "auctelis-out",
}


def _is_auctelis_output_dir(name: str) -> bool:
    """Skip scanner artifact dirs (auctelis-out, auctelis-out-pilot, …)."""
    return name == "auctelis-out" or name.startswith("auctelis-out-")


# Default authority-noise dirs (fixtures / docs / tests / canned demos).
# Opt out with ``default_excludes=False`` / ``scan --include-fixtures``.
_DEFAULT_EXCLUDE_DIRS = {
    "tests",
    "test",
    "examples",
    "example",
    "eval",
    "docs",
    "doc",
    "fixtures",
    "fixture",
    "testdata",
    "__tests__",
    "demo-vulnerable",
    "canonical",
}


def is_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def iter_repo_files(
    root: Path,
    *,
    limits: CollectorLimits,
    events: list[dict[str, Any]],
    default_excludes: bool = True,
) -> tuple[dict[str, Any], list[Path]]:
    """Bounded walk: respects max_depth, max_files, and max_file_bytes before any content read."""
    root = root.resolve()
    files: list[Path] = []
    file_count = 0
    symlink_count = 0
    skipped: list[str] = []
    truncated = False
    skip_dirs = set(_SKIP_DIRS)
    if default_excludes:
        skip_dirs |= _DEFAULT_EXCLUDE_DIRS

    def on_error(err: OSError) -> None:
        events.append({"type": "walk_error", "message": str(err)})

    for dirpath, dirnames, filenames in os.walk(root, onerror=on_error, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root)
        depth = 0 if str(rel_dir) == "." else len(rel_dir.parts)
        if depth >= limits.max_depth:
            dirnames[:] = []
            events.append({"type": "depth_limit", "path": str(rel_dir)})
            continue
        kept: list[str] = []
        for d in dirnames:
            if d in skip_dirs or _is_auctelis_output_dir(d):
                if d in _DEFAULT_EXCLUDE_DIRS and default_excludes:
                    events.append(
                        {
                            "type": "default_exclude",
                            "path": str(rel_dir / d if str(rel_dir) != "." else Path(d)),
                        }
                    )
                continue
            kept.append(d)
        dirnames[:] = kept
        for name in filenames:
            if file_count >= limits.max_files:
                truncated = True
                events.append({"type": "file_limit_reached", "path": str(rel_dir)})
                return (
                    {
                        "file_count": file_count,
                        "symlink_count": symlink_count,
                        "truncated": True,
                        "skipped_oversize": skipped,
                    },
                    files,
                )
            p = Path(dirpath) / name
            file_count += 1
            if p.is_symlink():
                symlink_count += 1
                events.append(
                    {
                        "type": "symlink_recorded_not_followed",
                        "path": str(p.relative_to(root)),
                    }
                )
                continue
            try:
                size = p.stat().st_size
            except OSError as exc:
                events.append(
                    {
                        "type": "stat_error",
                        "path": str(p.relative_to(root)),
                        "message": str(exc),
                    }
                )
                continue
            if size > limits.max_file_bytes:
                skipped.append(str(p.relative_to(root)))
                events.append(
                    {
                        "type": "parse_skipped_size",
                        "path": str(p.relative_to(root)),
                        "size": size,
                        "max_file_bytes": limits.max_file_bytes,
                    }
                )
                continue
            files.append(p)

    return (
        {
            "file_count": file_count,
            "symlink_count": symlink_count,
            "truncated": truncated,
            "skipped_oversize": skipped,
        },
        files,
    )


def safe_read_text(
    path: Path,
    *,
    root: Path,
    limits: CollectorLimits,
    events: list[dict[str, Any]],
    adapter: str,
) -> str | None:
    """Read text only after path, depth, and size checks. Never follows symlinks."""
    root = root.resolve()
    try:
        if path.is_symlink():
            events.append(
                {
                    "type": "symlink_read_skipped",
                    "adapter": adapter,
                    "path": str(path.relative_to(root)),
                }
            )
            return None
        resolved = path.resolve()
        if not is_under_root(resolved, root):
            events.append(
                {
                    "type": "path_escape_skipped",
                    "adapter": adapter,
                    "path": str(path),
                }
            )
            return None
        rel = resolved.relative_to(root)
        if len(rel.parts) > limits.max_depth:
            events.append(
                {
                    "type": "depth_limit",
                    "adapter": adapter,
                    "path": str(rel),
                }
            )
            return None
        size = resolved.stat().st_size
        if size > limits.max_file_bytes:
            events.append(
                {
                    "type": "parse_skipped_size",
                    "adapter": adapter,
                    "path": str(rel),
                    "size": size,
                }
            )
            return None
        with resolved.open("r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limits.max_file_bytes)
    except OSError as exc:
        events.append(
            {
                "type": "read_error",
                "adapter": adapter,
                "path": str(path),
                "message": str(exc),
            }
        )
        return None


def select_files(files: list[Path], predicate: Callable[[Path], bool]) -> Iterator[Path]:
    for path in files:
        if predicate(path):
            yield path
