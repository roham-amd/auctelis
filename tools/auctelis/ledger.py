"""Local hook heartbeat + recent-delta ledger (observed fire, not file presence).

The product screen must distinguish:
- wired but never observed
- firing (last heartbeat N ago)
- not_wired / not_armed

Hooks call ``record_heartbeat`` / ``append_delta``; ``hook status`` reads them.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HEARTBEAT_NAME = "heartbeat.json"
_LEDGER_NAME = "ledger.jsonl"
_MAX_LEDGER = 5


def auctelis_state_dir(*, home: Path | None = None) -> Path:
    return (home or Path.home()).expanduser() / ".auctelis"


def heartbeat_path(*, home: Path | None = None) -> Path:
    return auctelis_state_dir(home=home) / _HEARTBEAT_NAME


def ledger_path(*, home: Path | None = None) -> Path:
    return auctelis_state_dir(home=home) / _LEDGER_NAME


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_heartbeat_doc(doc: dict[str, Any], *, home: Path | None = None) -> Path:
    """Persist a heartbeat document (shared by CLI import and script fallback)."""
    root = auctelis_state_dir(home=home)
    root.mkdir(parents=True, exist_ok=True)
    path = heartbeat_path(home=home)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def record_heartbeat(
    *,
    home: Path | None = None,
    host: str = "session",
    event: str = "sessionStart",
    had_delta: bool = False,
    delta_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Write last-fired heartbeat; optionally append a delta ledger entry."""
    stamp = _now_iso()
    doc: dict[str, Any] = {
        "schema_version": "heartbeat/1",
        "last_fired": stamp,
        "host": host,
        "event": event,
        "had_delta": bool(had_delta),
        "last_delta": stamp if had_delta else None,
        "last_delta_lines": list(delta_lines or [])[:5] if had_delta else [],
    }
    prev = load_heartbeat(home=home)
    if prev and not had_delta:
        doc["last_delta"] = prev.get("last_delta")
        doc["last_delta_lines"] = list(prev.get("last_delta_lines") or [])[:5]
    write_heartbeat_doc(doc, home=home)
    if had_delta and delta_lines:
        append_delta(delta_lines, home=home, host=host, fired_at=stamp)
    return doc


def load_heartbeat(*, home: Path | None = None) -> dict[str, Any] | None:
    path = heartbeat_path(home=home)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def append_delta(
    lines: list[str],
    *,
    home: Path | None = None,
    host: str = "session",
    fired_at: str | None = None,
) -> None:
    root = auctelis_state_dir(home=home)
    root.mkdir(parents=True, exist_ok=True)
    path = ledger_path(home=home)
    entry = {
        "fired_at": fired_at or _now_iso(),
        "host": host,
        "lines": [str(x) for x in lines[:8] if str(x).strip()],
    }
    existing = load_ledger(home=home)
    existing.append(entry)
    trimmed = existing[-_MAX_LEDGER:]
    path.write_text(
        "".join(json.dumps(item, separators=(",", ":")) + "\n" for item in trimmed),
        encoding="utf-8",
        newline="\n",
    )


def load_ledger(*, home: Path | None = None) -> list[dict[str, Any]]:
    path = ledger_path(home=home)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out[-_MAX_LEDGER:]


def _age_label(iso: str | None) -> str:
    if not iso:
        return "never"
    try:
        stamp = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return str(iso)
    now = datetime.now(UTC)
    seconds = max(0, int((now - stamp).total_seconds()))
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def observed_state(heartbeat: dict[str, Any] | None) -> str:
    """Map heartbeat → status fragment for a wired host."""
    if not heartbeat or not heartbeat.get("last_fired"):
        return "wired, not yet observed"
    return f"firing (last: {_age_label(str(heartbeat.get('last_fired')))})"
