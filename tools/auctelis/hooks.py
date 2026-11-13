"""Install session-start and PreToolUse authority hooks.

Authority Watch front door: after ``doctor`` + ``lock --home``, install a
session-start hook that speaks only on change, and optionally the lock-enforcing
PreToolUse hook that refuses agent edits to authority-bearing paths.
"""

from __future__ import annotations

import contextlib
import json
import shutil
from pathlib import Path
from typing import Any

_SESSION_HOOK_NAME = "auctelis-session-delta.py"
_PRETOOL_HOOK_NAME = "claude_pretool_authority_hook.py"
_PRETOOL_SH_NAME = "claude-pretool-authority-hook.sh"


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def session_hook_source() -> Path:
    """Prefer packaged template; fall back to generating inline."""
    bundled = _templates_dir() / _SESSION_HOOK_NAME
    return bundled


def pretool_hook_sources() -> tuple[Path, Path]:
    return _templates_dir() / _PRETOOL_HOOK_NAME, _templates_dir() / _PRETOOL_SH_NAME


def default_hooks_dir(*, home: Path | None = None) -> Path:
    root = (home or Path.home()).expanduser()
    return root / ".auctelis" / "hooks"


def _write_session_hook(dest: Path) -> None:
    src = session_hook_source()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dest)
    else:
        dest.write_text(_SESSION_HOOK_FALLBACK, encoding="utf-8", newline="\n")
    with contextlib.suppress(OSError):
        dest.chmod(dest.stat().st_mode | 0o111)


def _write_pretool_hooks(dest_dir: Path) -> list[Path]:
    py_src, sh_src = pretool_hook_sources()
    written: list[Path] = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    for src, name in ((py_src, _PRETOOL_HOOK_NAME), (sh_src, _PRETOOL_SH_NAME)):
        if not src.is_file():
            continue
        dest = dest_dir / name
        shutil.copy2(src, dest)
        with contextlib.suppress(OSError):
            dest.chmod(dest.stat().st_mode | 0o111)
        written.append(dest)
    return written


def _merge_claude_settings(
    settings_path: Path,
    *,
    session_hook: Path | None,
    pretool_hook: Path | None,
) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if settings_path.is_file():
        try:
            loaded = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError):
            data = {}
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    def _ensure_cmd(event: str, command: str, matcher: str | None = None) -> None:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            entries = []
        # Drop prior auctelis entries for this event so reinstall is idempotent.
        kept: list[Any] = []
        for item in entries:
            if isinstance(item, dict):
                cmd = str(item.get("command") or "")
                if "auctelis" in cmd.lower() and (
                    "session-delta" in cmd
                    or "pretool_authority" in cmd
                    or "pretool-authority" in cmd
                ):
                    continue
            kept.append(item)
        entry: dict[str, Any] = {"type": "command", "command": command}
        if matcher:
            entry["matcher"] = matcher
        kept.append(entry)
        hooks[event] = kept

    if session_hook is not None:
        _ensure_cmd("SessionStart", str(session_hook))
    if pretool_hook is not None:
        _ensure_cmd("PreToolUse", str(pretool_hook), matcher="Edit|Write|Bash")
    return data


def install_hooks(
    *,
    home: Path | None = None,
    hooks_dir: Path | None = None,
    session: bool = True,
    pretool: bool = True,
    wire_claude: bool = True,
) -> dict[str, Any]:
    """Copy hook scripts and optionally wire Claude Code settings.json."""
    home_root = (home or Path.home()).expanduser()
    dest_dir = hooks_dir or default_hooks_dir(home=home_root)
    dest_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "hooks_dir": str(dest_dir),
        "session_hook": None,
        "pretool_hooks": [],
        "claude_settings": None,
        "messages": [],
    }

    session_path: Path | None = None
    if session:
        session_path = dest_dir / _SESSION_HOOK_NAME
        _write_session_hook(session_path)
        result["session_hook"] = str(session_path)
        result["messages"].append(f"Wrote session-start delta hook → {session_path}")

    pretool_paths: list[Path] = []
    if pretool:
        pretool_paths = _write_pretool_hooks(dest_dir)
        result["pretool_hooks"] = [str(p) for p in pretool_paths]
        for p in pretool_paths:
            result["messages"].append(f"Wrote PreToolUse lock hook → {p}")

    if wire_claude:
        settings = home_root / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        pretool_cmd = None
        for p in pretool_paths:
            if p.suffix == ".py":
                pretool_cmd = p
                break
        if pretool_cmd is None and pretool_paths:
            pretool_cmd = pretool_paths[0]
        merged = _merge_claude_settings(
            settings,
            session_hook=session_path,
            pretool_hook=pretool_cmd,
        )
        settings.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8", newline="\n")
        result["claude_settings"] = str(settings)
        result["messages"].append(f"Wired Claude Code hooks in {settings}")

    if not result["messages"]:
        result["messages"].append("Nothing to install (session and pretool both disabled).")
    result["messages"].append(
        "Next: `auctelis lock --home`, then open a new agent session — "
        "delta prints only when authority changed."
    )
    return result


_SESSION_HOOK_FALLBACK = '''#!/usr/bin/env python3
"""SessionStart: print host authority delta vs ~/.auctelis/AUTHORITY.lock (quiet if none)."""
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
    return 0  # never block session start


if __name__ == "__main__":
    raise SystemExit(main())
'''
