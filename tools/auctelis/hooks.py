"""Install session-start and tool-time authority hooks for Claude and Cursor.

Authority Watch front door: after ``auctelis watch --seal``, install a
session-start hook that speaks only on change, and a tool-time hook that refuses
unlisted MCP servers and agent edits to authority-bearing paths.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

_SESSION_HOOK_NAME = "auctelis-session-delta.py"
_PRETOOL_HOOK_NAME = "claude_pretool_authority_hook.py"
_PRETOOL_SH_NAME = "claude-pretool-authority-hook.sh"
_CURSOR_HOOK_NAME = "auctelis_cursor_hook.py"

_CLAUDE_EVENTS = ("SessionStart", "PreToolUse")
_CURSOR_EVENTS = ("sessionStart", "beforeMCPExecution", "beforeShellExecution", "beforeFileEdit")


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def session_hook_source() -> Path:
    """Prefer packaged template; fall back to generating inline."""
    bundled = _templates_dir() / _SESSION_HOOK_NAME
    return bundled


def pretool_hook_sources() -> tuple[Path, Path]:
    return _templates_dir() / _PRETOOL_HOOK_NAME, _templates_dir() / _PRETOOL_SH_NAME


def cursor_hook_source() -> Path:
    return _templates_dir() / _CURSOR_HOOK_NAME


def default_hooks_dir(*, home: Path | None = None) -> Path:
    root = (home or Path.home()).expanduser()
    return root / ".auctelis" / "hooks"


def default_cursor_hooks_file(*, home: Path | None = None) -> Path:
    return (home or Path.home()).expanduser() / ".cursor" / "hooks.json"


def _hook_command(path: Path) -> str:
    """Quote both interpreter and script so Windows and POSIX both work."""
    return f'"{sys.executable}" "{path}"'


def _write_session_hook(dest: Path) -> None:
    src = session_hook_source()
    if not src.is_file():
        raise FileNotFoundError(f"packaged session hook missing: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
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


def _write_cursor_hook(dest_dir: Path) -> Path | None:
    src = cursor_hook_source()
    if not src.is_file():
        return None
    dest = dest_dir / _CURSOR_HOOK_NAME
    shutil.copy2(src, dest)
    with contextlib.suppress(OSError):
        dest.chmod(dest.stat().st_mode | 0o111)
    return dest


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _backup_corrupt_json(path: Path) -> Path | None:
    """Preserve a user settings file that is not valid JSON before we rewrite it."""
    if not path.is_file():
        return None
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return None
    except (OSError, json.JSONDecodeError):
        backup = path.with_name(f"{path.name}.auctelis-bak")
        with contextlib.suppress(OSError):
            shutil.copy2(path, backup)
            return backup
    return None


def _is_auctelis_entry(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    commands = [str(item.get("command") or "")]
    for nested in item.get("hooks") or []:
        if isinstance(nested, dict):
            commands.append(str(nested.get("command") or ""))
    blob = " ".join(commands).lower()
    return "auctelis" in blob and (
        "session-delta" in blob
        or "pretool_authority" in blob
        or "pretool-authority" in blob
        or "auctelis_cursor_hook" in blob
    )


def _merge_claude_settings(
    settings_path: Path,
    *,
    session_hook: str | None,
    pretool_hook: str | None,
) -> dict[str, Any]:
    data = _load_json_object(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    def _ensure_cmd(event: str, command: str, matcher: str | None = None) -> None:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            entries = []
        kept = [item for item in entries if not _is_auctelis_entry(item)]
        entry: dict[str, Any] = {"type": "command", "command": command}
        if matcher:
            entry["matcher"] = matcher
        kept.append(entry)
        hooks[event] = kept

    if session_hook is not None:
        _ensure_cmd("SessionStart", session_hook)
    if pretool_hook is not None:
        # `.*` reaches MCP tool calls too; the old Edit|Write|Bash matcher never
        # let the allowlist check see `mcp__…`.
        _ensure_cmd("PreToolUse", pretool_hook, matcher=".*")
    return data


def _merge_cursor_hooks(
    settings_path: Path,
    *,
    session_hook: str | None,
    pretool_hook: str | None,
) -> dict[str, Any]:
    data = _load_json_object(settings_path)
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks

    def _ensure_cmd(event: str, command: str) -> None:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            entries = []
        kept = [item for item in entries if not _is_auctelis_entry(item)]
        kept.append({"command": command})
        hooks[event] = kept

    if session_hook is not None:
        _ensure_cmd("sessionStart", session_hook)
    if pretool_hook is not None:
        for event in ("beforeMCPExecution", "beforeShellExecution", "beforeFileEdit"):
            _ensure_cmd(event, pretool_hook)
    return data


def install_hooks(
    *,
    home: Path | None = None,
    hooks_dir: Path | None = None,
    session: bool = True,
    pretool: bool = True,
    wire_claude: bool = True,
    wire_cursor: bool = True,
    cursor_hooks_file: Path | None = None,
) -> dict[str, Any]:
    """Copy hook scripts and wire Claude Code and Cursor host settings."""
    home_root = (home or Path.home()).expanduser()
    dest_dir = hooks_dir or default_hooks_dir(home=home_root)
    dest_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "hooks_dir": str(dest_dir),
        "session_hook": None,
        "pretool_hooks": [],
        "cursor_hook": None,
        "claude_settings": None,
        "cursor_settings": None,
        "messages": [],
    }

    session_path: Path | None = None
    if session:
        session_path = dest_dir / _SESSION_HOOK_NAME
        _write_session_hook(session_path)
        result["session_hook"] = str(session_path)
        result["messages"].append(f"Wrote session-start delta hook → {session_path}")

    pretool_paths: list[Path] = []
    cursor_path: Path | None = None
    if pretool:
        pretool_paths = _write_pretool_hooks(dest_dir)
        result["pretool_hooks"] = [str(p) for p in pretool_paths]
        for path in pretool_paths:
            result["messages"].append(f"Wrote PreToolUse lock hook → {path}")
        cursor_path = _write_cursor_hook(dest_dir)
        if cursor_path is not None:
            result["cursor_hook"] = str(cursor_path)
            result["messages"].append(f"Wrote Cursor lock hook → {cursor_path}")

    session_cmd = _hook_command(session_path) if session_path is not None else None
    pretool_cmd: str | None = None
    for path in pretool_paths:
        if path.suffix == ".py":
            pretool_cmd = _hook_command(path)
            break
    if pretool_cmd is None and pretool_paths:
        pretool_cmd = _hook_command(pretool_paths[0])

    if wire_claude:
        settings = home_root / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        backup = _backup_corrupt_json(settings)
        if backup is not None:
            result["messages"].append(f"Backed up corrupt Claude settings → {backup}")
        merged = _merge_claude_settings(
            settings,
            session_hook=session_cmd,
            pretool_hook=pretool_cmd,
        )
        settings.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8", newline="\n")
        result["claude_settings"] = str(settings)
        result["messages"].append(f"Wired Claude Code hooks in {settings}")

    if wire_cursor:
        cursor_settings = cursor_hooks_file or default_cursor_hooks_file(home=home_root)
        cursor_settings.parent.mkdir(parents=True, exist_ok=True)
        backup = _backup_corrupt_json(cursor_settings)
        if backup is not None:
            result["messages"].append(f"Backed up corrupt Cursor hooks → {backup}")
        cursor_cmd = _hook_command(cursor_path) if cursor_path is not None else pretool_cmd
        merged_cursor = _merge_cursor_hooks(
            cursor_settings,
            session_hook=session_cmd,
            pretool_hook=cursor_cmd,
        )
        cursor_settings.write_text(
            json.dumps(merged_cursor, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        result["cursor_settings"] = str(cursor_settings)
        result["messages"].append(f"Wired Cursor hooks in {cursor_settings}")

    if not result["messages"]:
        result["messages"].append("Nothing to install (session and pretool both disabled).")
    result["messages"].append(
        "Next: `auctelis watch --seal` if you have not sealed a baseline — "
        "then a new session prints only authority changes."
    )
    return result


def _event_commands(entries: Any) -> list[str]:
    commands: list[str] = []
    if not isinstance(entries, list):
        return commands
    for item in entries:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command") or "").strip()
        if command:
            commands.append(command)
        for nested in item.get("hooks") or []:
            if isinstance(nested, dict):
                nested_command = str(nested.get("command") or "").strip()
                if nested_command:
                    commands.append(nested_command)
    return commands


def _host_state(
    settings_path: Path,
    *,
    events: tuple[str, ...],
    hooks_dir: Path,
    lock_present: bool,
    cli_on_path: bool,
) -> dict[str, Any]:
    data = _load_json_object(settings_path)
    raw_hooks = data.get("hooks")
    hooks: dict[str, Any] = raw_hooks if isinstance(raw_hooks, dict) else {}
    wired_events: list[str] = []
    script_present = False
    for event in events:
        commands = _event_commands(hooks.get(event))
        for command in commands:
            if "auctelis" not in command.lower():
                continue
            wired_events.append(event)
            for name in (_SESSION_HOOK_NAME, _PRETOOL_HOOK_NAME, _CURSOR_HOOK_NAME):
                if name in command and (hooks_dir / name).is_file():
                    script_present = True
            break
    wired = bool(wired_events)
    if not wired:
        state = "not_wired"
    elif not script_present or not cli_on_path:
        state = "not_firing"
    elif not lock_present:
        state = "not_armed"
    else:
        state = "firing"
    return {
        "wired": wired,
        "events": list(dict.fromkeys(wired_events)),
        "state": state,
        "settings": str(settings_path),
    }


def hook_status(
    *,
    home: Path | None = None,
    hooks_dir: Path | None = None,
    settings_file: Path | None = None,
    cursor_hooks_file: Path | None = None,
) -> dict[str, Any]:
    """Report whether each host is wired and able to fire."""
    home_root = (home or Path.home()).expanduser()
    directory = hooks_dir or default_hooks_dir(home=home_root)
    lock_path = home_root / ".auctelis" / "AUTHORITY.lock"
    lock_present = lock_path.is_file()
    cli = shutil.which("auctelis")
    claude_settings = settings_file or (home_root / ".claude" / "settings.json")
    cursor_settings = cursor_hooks_file or default_cursor_hooks_file(home=home_root)
    return {
        "lock": str(lock_path),
        "lock_present": lock_present,
        "cli_on_path": cli is not None,
        "hooks_dir": str(directory),
        "claude": _host_state(
            claude_settings,
            events=_CLAUDE_EVENTS,
            hooks_dir=directory,
            lock_present=lock_present,
            cli_on_path=cli is not None,
        ),
        "cursor": _host_state(
            cursor_settings,
            events=_CURSOR_EVENTS,
            hooks_dir=directory,
            lock_present=lock_present,
            cli_on_path=cli is not None,
        ),
    }


def render_hook_status(status: dict[str, Any]) -> str:
    lines = ["auctelis hook status"]
    for label, key in (("Claude Code", "claude"), ("Cursor", "cursor")):
        host = status.get(key) or {}
        state = str(host.get("state") or "not_wired")
        events = ", ".join(host.get("events") or [])
        detail = f" ({events})" if events else ""
        lines.append(f"{label}: {state}{detail}")
    lock = "present" if status.get("lock_present") else "missing — run `auctelis watch --seal`"
    lines.append(f"Lock: {status.get('lock')} ({lock})")
    if not status.get("cli_on_path"):
        lines.append("CLI: auctelis not on PATH — hooks cannot fire.")
    return "\n".join(lines)
