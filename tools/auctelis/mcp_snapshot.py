"""MCP ``tools/list`` snapshot + description-hash pin.

Default mode is **file** (no process spawn). Opt-in ``--execute`` launches a
local command with scrubbed env. Network is **not** blocked by this module —
``--allow-network`` only records intent; use OS sandboxing for hard isolation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from auctelis.process_env import scrub_env


@dataclass(slots=True)
class ToolSnapshot:
    name: str
    description_hash: str
    description_preview: str
    input_schema_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description_sha256": self.description_hash,
            "description_preview": self.description_preview,
            "input_schema_keys": self.input_schema_keys,
        }


def _hash_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def tools_from_list_payload(payload: Any) -> list[ToolSnapshot]:
    tools_raw: list[Any]
    if isinstance(payload, dict):
        nested = payload.get("result")
        if isinstance(nested, dict) and "tools" in nested:
            tools_raw = list(nested.get("tools") or [])
        else:
            tools_raw = list(payload.get("tools") or [])
    elif isinstance(payload, list):
        tools_raw = payload
    else:
        tools_raw = []
    out: list[ToolSnapshot] = []
    for tool in tools_raw:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "")
        desc = str(tool.get("description") or "")
        schema = tool.get("inputSchema") or tool.get("input_schema") or {}
        keys = sorted(schema.get("properties", {}).keys()) if isinstance(schema, dict) else []
        out.append(
            ToolSnapshot(
                name=name,
                description_hash=_hash_text(desc),
                description_preview=desc[:160].replace("\n", " "),
                input_schema_keys=[str(k) for k in keys[:40]],
            )
        )
    return out


def snapshot_from_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tools = tools_from_list_payload(data)
    return {
        "mode": "file",
        "ok": True,
        "source": str(path),
        "tool_count": len(tools),
        "tools": [t.to_dict() for t in tools],
        "authority_lock_fragment": {
            "version": 1,
            "mcp_tools": {t.name: t.description_hash for t in tools if t.name},
        },
    }


def snapshot_execute(
    command: list[str],
    *,
    allow_network: bool = False,
    timeout_s: float = 30.0,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run ``command`` expecting JSON tools/list on stdout."""
    if not command:
        raise ValueError("command required")
    exe = command[0]
    if any(ch in exe for ch in ("|", ";", "&", ">", "<", "`", "\n")):
        raise ValueError(f"refusing executable with shell metacharacters: {exe!r}")

    extra = {"AUCTELIS_SNAPSHOT": "1"}
    if not allow_network:
        extra["AUCTELIS_NO_NETWORK"] = "1"  # advisory hint only
    env = scrub_env(extra=extra)

    with tempfile.TemporaryDirectory(prefix="auctelis-snap-") as tmp:
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(cwd) if cwd else tmp,
            env=env,
        )
    if proc.returncode != 0:
        return {
            "mode": "execute",
            "ok": False,
            "returncode": proc.returncode,
            "stderr_preview": (proc.stderr or "")[:400],
            "tool_count": 0,
            "tools": [],
            "limitations": [
                "Child exited non-zero; env was scrubbed but OS network/FS were not sandboxed.",
            ],
        }
    try:
        payload = json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        return {
            "mode": "execute",
            "ok": False,
            "error": f"stdout was not JSON: {exc}",
            "stdout_preview": (proc.stdout or "")[:400],
            "tool_count": 0,
            "tools": [],
        }
    tools = tools_from_list_payload(payload)
    return {
        "mode": "execute",
        "ok": True,
        "allow_network": allow_network,
        "network_enforced": False,
        "tool_count": len(tools),
        "tools": [t.to_dict() for t in tools],
        "authority_lock_fragment": {
            "version": 1,
            "mcp_tools": {t.name: t.description_hash for t in tools if t.name},
        },
        "limitations": [
            "Process ran with scrubbed env only; OS network/FS sandbox is best-effort.",
            "Pin description hashes into AUTHORITY.lock and re-diff on upgrades.",
            "`allow_network` records intent only — it does not open or close sockets.",
        ],
    }


def diff_tool_locks(base: dict[str, str], head: dict[str, str]) -> dict[str, Any]:
    added = sorted(set(head) - set(base))
    removed = sorted(set(base) - set(head))
    changed = sorted(k for k in set(base) & set(head) if base[k] != head[k])
    return {
        "tools_added": added,
        "tools_removed": removed,
        "description_hash_changed": changed,
        "rug_pull_suspect": bool(changed),
    }
