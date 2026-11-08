"""Structural parser for Claude Code project/user settings.

Catches the authority surfaces the host-marker adapter previously ignored:
hooks in settings, permission bypass, project-MCP auto-approve, and base-URL
overrides.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.jsonc import loads_json_tolerant
from authdiff.inventory.limits import CollectorLimits

_DOWNLOAD_EXEC_RE = re.compile(
    r"(curl\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"wget\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"\$\(\s*env\s*\)|\$\{\s*env\s*\})",
    re.IGNORECASE,
)
_BASE_URL_KEYS = {
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_URL",
    "OPENAI_BASE_URL",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "ALL_PROXY",
}


def _is_claude_settings(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    if name in {"settings.json", "settings.local.json"} and (
        "/.claude/" in f"/{rel}" or rel.startswith(".claude/")
    ):
        return True
    return rel in {".claude/settings.json", ".claude/settings.local.json"}


def _walk_hooks(hooks_obj: Any) -> list[tuple[str, str]]:
    """Return (event_name, command_text) pairs from Claude hooks blocks."""
    found: list[tuple[str, str]] = []
    if not isinstance(hooks_obj, dict):
        return found
    for event, entries in hooks_obj.items():
        event_name = str(event)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    cmd = entry.get("command") or entry.get("bash") or entry.get("shell")
                    if cmd:
                        found.append((event_name, str(cmd)))
                    matcher = entry.get("hooks") or entry.get("matcher")
                    if isinstance(matcher, list):
                        for sub in matcher:
                            if isinstance(sub, dict):
                                sub_cmd = sub.get("command") or sub.get("bash")
                                if sub_cmd:
                                    found.append((event_name, str(sub_cmd)))
                elif isinstance(entry, str):
                    found.append((event_name, entry))
        elif isinstance(entries, dict):
            cmd = entries.get("command") or entries.get("bash")
            if cmd:
                found.append((event_name, str(cmd)))
        elif isinstance(entries, str):
            found.append((event_name, entries))
    return found


def discover_claude_settings(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in select_files(files, lambda p: _is_claude_settings(p, root)):
        rel = path.relative_to(root).as_posix()
        raw = safe_read_text(
            path, root=root, limits=limits, events=events, adapter="claude_settings"
        )
        if raw is None:
            events.append(
                {
                    "type": "unparsed_agent_config",
                    "adapter": "claude_settings",
                    "path": rel,
                    "message": "Claude settings could not be read",
                }
            )
            continue
        try:
            data = loads_json_tolerant(raw)
        except json.JSONDecodeError as exc:
            events.append(
                {
                    "type": "parse_error",
                    "adapter": "claude_settings",
                    "path": rel,
                    "message": str(exc),
                    "agent_config": True,
                }
            )
            events.append(
                {
                    "type": "unparsed_agent_config",
                    "adapter": "claude_settings",
                    "path": rel,
                    "message": str(exc),
                }
            )
            continue
        if not isinstance(data, dict):
            continue

        hints: list[str] = ["claude_settings"]
        detail: dict[str, Any] = {}

        if data.get("enableAllProjectMcpServers") is True:
            hints.append("project_mcp_auto_approve")
            detail["enableAllProjectMcpServers"] = True

        perm = data.get("permissions") or data.get("permissionMode") or data.get("permission_mode")
        perm_s = json.dumps(perm).lower() if perm is not None else ""
        if "bypass" in perm_s or data.get("permissionMode") == "bypassPermissions":
            hints.append("permission_bypass_flag")
        allow: list[Any] = []
        if isinstance(perm, dict):
            raw_allow = perm.get("allow")
            if raw_allow is None:
                raw_allow = perm.get("defaultMode")
            if isinstance(raw_allow, str):
                allow = [raw_allow]
            elif isinstance(raw_allow, list):
                allow = list(raw_allow)
        joined_allow = " ".join(str(a) for a in allow)
        if "bash(*)" in joined_allow.lower() or "bash(*)" in perm_s:
            hints.append("wildcard_bash_permission")
            hints.append("permission_bypass_flag")

        env = data.get("env") or data.get("environment") or {}
        if isinstance(env, dict):
            for key in env:
                if str(key).upper() in _BASE_URL_KEYS:
                    hints.append("base_url_or_proxy_override")
                    detail["override_key"] = str(key)
                    break

        hooks = data.get("hooks")
        hook_pairs = _walk_hooks(hooks)
        for event_name, cmd in hook_pairs:
            event_l = event_name.lower()
            if event_l in {
                "sessionstart",
                "session_start",
                "pretooluse",
                "pre_tool_use",
                "userpromptsubmit",
            }:
                hints.append("pre_execution_lifecycle")
                hints.append("auto_running_hook")
            # Only curl|sh / wget|sh style pipes are download-and-execute; bare
            # `curl` (e.g. Slack notification) is network egress, not RCE.
            if _DOWNLOAD_EXEC_RE.search(cmd):
                hints.append("download_and_execute")
                hints.append("possible_execution_boundary")
            elif re.search(r"\bcurl\b|\bwget\b|\biwr\b", cmd, re.IGNORECASE):
                hints.append("network_egress_in_hook")
                hints.append("possible_execution_boundary")
            if "$(env)" in cmd or "${env}" in cmd.lower() or "printenv" in cmd.lower():
                hints.append("env_capture_in_hook")
                hints.append("download_and_execute")

        if hook_pairs:
            detail["hook_events"] = sorted({e for e, _ in hook_pairs})
            detail["hook_count"] = len(hook_pairs)

        if len(hints) <= 1:
            # Still record the settings file as a host settings surface.
            hints.append("host_declared_configuration")

        results.append(
            {
                "name": f"claude-settings:{path.name}",
                "type": "Host Settings",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "claude_settings",
                "adapter_maturity": "SUPPORTED",
                "discovery_status": "IDENTIFIED",
                "host_id": "claude-code",
                "priority_hints": sorted(set(hints)),
                "settings_detail": detail,
            }
        )

        # Emit one Hook component per auto-running hook for RULE-004 / RULE-015.
        for event_name, cmd in hook_pairs:
            hook_hints = ["possible_execution_boundary"]
            if event_name.lower() in {
                "sessionstart",
                "session_start",
                "pretooluse",
                "pre_tool_use",
            }:
                hook_hints.append("pre_execution_lifecycle")
            if _DOWNLOAD_EXEC_RE.search(cmd) or "$(env)" in cmd:
                hook_hints.append("download_and_execute")
            results.append(
                {
                    "name": f"{event_name}",
                    "type": "Hook",
                    "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                    "repository_path": rel,
                    "adapter": "claude_settings",
                    "adapter_maturity": "SUPPORTED",
                    "discovery_status": "IDENTIFIED",
                    "command": cmd[:240],
                    "priority_hints": hook_hints,
                }
            )

    return results
