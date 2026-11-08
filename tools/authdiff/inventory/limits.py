from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CollectorLimits:
    max_files: int = 5000
    max_depth: int = 12
    max_file_bytes: int = 2_000_000
