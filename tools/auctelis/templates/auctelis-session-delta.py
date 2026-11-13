#!/usr/bin/env python3
"""SessionStart: print host authority delta vs ~/.auctelis/AUTHORITY.lock (quiet if none).

Install via: ``auctelis hook install``
Requires: ``auctelis`` on PATH and a prior ``auctelis lock --home``.
"""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    try:
        proc = subprocess.run(
            ["auctelis", "doctor", "--since-lock"],
            check=False,
            capture_output=True,
            text=True,
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
