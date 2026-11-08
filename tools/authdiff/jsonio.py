"""Shared JSON read/write helpers (DRY I/O for CLI and orchestrators)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

type JsonValue = Any


def dumps_pretty(data: JsonValue) -> str:
    return json.dumps(data, indent=2) + "\n"


def print_json(data: JsonValue) -> None:
    print(dumps_pretty(data), end="")


def read_json(path: Path) -> JsonValue:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_pretty(data), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
