from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file_digest(path: Path, expected_hex: str) -> tuple[bool, str]:
    actual = sha256_file(path)
    return actual.lower() == expected_hex.lower(), actual
