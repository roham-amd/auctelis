#!/usr/bin/env python3
"""SessionStart: print host authority delta vs ~/.auctelis/AUTHORITY.lock (quiet if none).

Install via: ``auctelis hook install`` (or ``auctelis watch --arm``)
Requires: ``auctelis`` on PATH and a prior ``auctelis watch --seal``.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys


def _utf8_stdout() -> None:
    """Windows consoles default to cp1252; authority cards use `→`/`·`."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(OSError, ValueError):
            reconfigure(encoding="utf-8", errors="replace")


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
