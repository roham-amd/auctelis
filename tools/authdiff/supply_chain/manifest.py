from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from authdiff import __version__
from authdiff.supply_chain.digest import sha256_file


def build_digest_manifest(root: Path, *, max_files: int = 2000) -> dict:
    root = root.resolve()
    entries: list[dict] = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            d for d in dirnames if d not in {".git", "node_modules", ".venv", "venv", "__pycache__"}
        ]
        for name in filenames:
            if count >= max_files:
                break
            p = Path(dirpath) / name
            if p.is_symlink():
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            rel = p.relative_to(root).as_posix()
            entries.append(
                {
                    "relative_path": rel,
                    "sha256": sha256_file(p),
                    "size_bytes": size,
                }
            )
            count += 1

    return {
        "manifest_version": "1.0",
        "root_path": str(root),
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": {"name": "authdiff", "version": __version__},
        "entries": sorted(entries, key=lambda e: e["relative_path"]),
        "limitations": [
            "Digest computed only; signature, signer trust, and provenance are NOT verified.",
            "Symlinks are not followed.",
        ],
    }
