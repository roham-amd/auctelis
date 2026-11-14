#!/usr/bin/env python3
"""SessionStart: print host authority delta vs ~/.auctelis/AUTHORITY.lock (quiet if none).

Install via: ``auctelis hook install`` (or ``auctelis watch --arm``)
Requires: ``auctelis`` on PATH and a prior ``auctelis watch --seal``.

Always writes a local heartbeat so ``auctelis hook status`` can distinguish
wired-but-never-observed from actually firing. This is a tripwire watch, not a gate.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
from pathlib import Path


def _utf8_stdout() -> None:
    """Windows consoles default to cp1252; authority cards use `→`/`·`."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(OSError, ValueError):
            reconfigure(encoding="utf-8", errors="replace")


def _record_heartbeat(had_delta: bool, lines: list[str]) -> None:
    """Best-effort: prefer packaged ledger; else write heartbeat.json only."""
    home = Path.home()
    try:
        from auctelis.ledger import record_heartbeat

        record_heartbeat(
            home=home,
            host="session",
            event="sessionStart",
            had_delta=had_delta,
            delta_lines=lines,
        )
        return
    except Exception:
        pass
    # Copied script may lack the package on PYTHONPATH — still leave a heartbeat.
    import json
    from datetime import UTC, datetime

    root = home / ".auctelis"
    with contextlib.suppress(OSError):
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        doc = {
            "schema_version": "heartbeat/1",
            "last_fired": stamp,
            "host": "session",
            "event": "sessionStart",
            "had_delta": had_delta,
            "last_delta": stamp if had_delta else None,
            "last_delta_lines": lines[:5] if had_delta else [],
        }
        (root / "heartbeat.json").write_text(
            json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n"
        )


def main() -> int:
    _utf8_stdout()
    try:
        proc = subprocess.run(
            ["auctelis", "watch", "--delta-only"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        print("auctelis: CLI not on PATH; skip session delta.", file=sys.stderr)
        return 0
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    lines = [line for line in out.splitlines() if line.strip()] if out else []
    had_delta = proc.returncode == 1 and bool(lines)
    _record_heartbeat(had_delta=had_delta or proc.returncode == 2, lines=lines)
    # Speak only on change (exit 1) or lock problems (exit 2).
    if proc.returncode == 0:
        return 0
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    # Never block session start — this is a watch, not a gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
