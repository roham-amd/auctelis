"""Authority broker MVP — ``auctelis run -- <server cmd>``.

Scrubs inherited secrets from the child environment and optionally records a
pinned ``AUTHORITY.lock`` path for the child. This is **not** a full MCP
stdio proxy; pair with ``auctelis snapshot`` to pin tool description hashes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from auctelis.lock_io import load_authority_lock
from auctelis.process_env import scrub_env

# Backward-compatible re-export (tests / older imports).
__all__ = ["load_authority_lock", "run_brokered"]


def run_brokered(
    command: list[str],
    *,
    lock_path: Path | None = None,
    cwd: Path | None = None,
) -> int:
    if not command:
        raise ValueError("command required after --")
    # Reject shell metacharacters in the executable path segment only — args stay literal.
    exe = command[0]
    if any(ch in exe for ch in ("|", ";", "&", ">", "<", "`", "\n")):
        raise ValueError(f"refusing executable with shell metacharacters: {exe!r}")

    env = scrub_env(extra={"AUCTELIS_BROKER": "1"})
    lock_meta: dict[str, Any] = {}
    if lock_path is not None:
        lock = load_authority_lock(lock_path)
        pinned = lock.get("mcp_tools") or {}
        lock_meta = {
            "lock": str(lock_path.resolve()),
            "pinned_tools": len(pinned) if isinstance(pinned, dict) else 0,
        }
        env["AUCTELIS_LOCK"] = str(lock_path.resolve())

    print(
        json.dumps(
            {
                "broker": "auctelis.run",
                "command_argc": len(command),
                "executable": exe,
                "env_key_count": len(env),
                "lock": lock_meta,
                "limitations": [
                    "Environment scrubbed; network/filesystem are NOT sandboxed.",
                    "AUTHORITY.lock is advisory to the child until a full MCP proxy ships.",
                    "Pair with `auctelis snapshot` to pin tool description hashes.",
                ],
            },
            indent=2,
        )
    )
    proc = subprocess.run(
        command,
        check=False,
        cwd=str(cwd) if cwd else None,
        env=env,
    )
    return int(proc.returncode)
