"""One-line authority cards for the terminal, session hook, and PR comment.

The product sentence is a declared-config diff:

    + mcp "linear" → mcp.linear.app · network · unpinned · publisher NOT VERIFIED

Only four fields are user-facing: name, destination (host or launcher),
capability set, and evidence strength. Everything else in the lock stays
available to tooling but does not become the page.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

_KIND_LABELS: dict[str, str] = {
    "mcp server registration": "mcp",
    "mcp server": "mcp",
    "server": "mcp",
    "hook": "hook",
    "skill": "skill",
    "ci workflow": "ci",
    "host settings": "host",
    "claude slash command": "command",
    "commands": "command",
    "plugin": "plugin",
    "subagent": "subagent",
    "rule / instruction file": "instructions",
    "rule pack": "instructions",
}

_CAP_LABELS: dict[str, str] = {
    "access_network": "network",
    "network": "network",
    "external_communication": "network",
    "access_secrets": "secrets",
    "secrets": "secrets",
    "credential_access": "secrets",
    "execute": "execute",
    "execute_commands": "execute",
    "command_execution": "execute",
    "modify_agent_instructions": "instructions",
    "instructions": "instructions",
    "read_files": "files",
    "write_files": "files",
    "filesystem": "files",
    "file_access": "files",
    "invoke_tools": "tools",
    "tool_invocation": "tools",
    "modify_approvals": "approvals",
    "unattended_operation": "unattended",
    "network_egress": "network",
    "credential_read": "secrets",
}

_MCP_KINDS = {"mcp"}
_PUBLISHER = "publisher NOT VERIFIED"
_NOISE_KINDS = {"agent host"}


def kind_label(kind: str | None) -> str:
    text = str(kind or "").strip()
    return _KIND_LABELS.get(text.lower(), text.lower() or "authority")


def _capabilities(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for raw in record.get("capabilities") or []:
        label = _CAP_LABELS.get(str(raw).strip().lower(), str(raw).strip().lower())
        if label and label not in out:
            out.append(label)
    return out


def _host_from(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "://" in text:
        try:
            return str(urlparse(text).hostname or "").lower()
        except ValueError:
            return ""
    host = text.split("/", 1)[0]
    return host.lower() if "." in host else ""


def destination(record: dict[str, Any]) -> str:
    """Best single destination: URL host, then declared destination host."""
    explicit = str(record.get("url_host") or "").strip().lower()
    if explicit:
        return explicit
    for item in record.get("destinations") or []:
        host = _host_from(item)
        if host:
            return host
    return ""


def launcher(record: dict[str, Any]) -> str:
    text = str(record.get("launcher") or "").strip()
    if not text:
        return ""
    return text.replace("\\", "/").rsplit("/", 1)[-1] if "/" in text else text


def _short(value: str, *, width: int = 44) -> str:
    text = str(value or "").strip()
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _pin_bit(record: dict[str, Any]) -> str:
    raw = str(record.get("pin_state") or "").strip().lower()
    if raw == "floating":
        return "unpinned"
    if raw == "digest":
        return "digest"
    if raw == "pinned":
        return "pinned"
    return ""


def record_card(record: dict[str, Any], *, prefix: str = "+") -> str:
    """Render one added/current authority record as a single card line."""
    kind = kind_label(record.get("kind"))
    name = str(record.get("name") or record.get("id") or "?").strip()
    path = str(record.get("path") or "").replace("\\", "/")
    host = destination(record)
    launch = launcher(record)

    bits: list[str] = []
    target = ""
    if host:
        target = f" → {host}"
    elif launch:
        target = f" launcher {_short(launch)}"
        if path:
            target += f" @ {path}"
    elif path:
        target = f" @ {path}"

    caps = _capabilities(record)
    bits.append(" · ".join(caps) if caps else "authority")
    pin = _pin_bit(record)
    if kind in _MCP_KINDS and pin:
        bits.append(pin)
    bits.append(_PUBLISHER)
    return f'{prefix} {kind} "{name}"{target} · ' + " · ".join(bits)


def _hosts(record: dict[str, Any]) -> set[str]:
    hosts = {str(record.get("url_host") or "").strip().lower()}
    for item in record.get("destinations") or []:
        hosts.add(_host_from(item))
    return {h for h in hosts if h}


def _set_delta(before: Any, after: Any) -> tuple[list[str], list[str]]:
    b = {str(x) for x in (before or []) if str(x)}
    a = {str(x) for x in (after or []) if str(x)}
    return sorted(a - b), sorted(b - a)


def changed_card(item: dict[str, Any], *, prefix: str = "~") -> str:
    """Render an existing record whose authority fields changed (old → new)."""
    before = item.get("before") or {}
    after = item.get("after") or {}
    kind = kind_label(after.get("kind") or before.get("kind"))
    name = str(after.get("name") or before.get("name") or item.get("id") or "?").strip()
    bits: list[str] = []

    before_hosts, after_hosts = _hosts(before), _hosts(after)
    added_hosts = sorted(after_hosts - before_hosts)
    removed_hosts = sorted(before_hosts - after_hosts)
    if added_hosts or removed_hosts:
        old = ", ".join(sorted(before_hosts)) or "∅"
        new = ", ".join(sorted(after_hosts)) or "∅"
        bits.append(f"host: {old} → {new}")

    old_launcher, new_launcher = launcher(before), launcher(after)
    if old_launcher != new_launcher:
        bits.append(f"launcher: {old_launcher or '∅'} → {new_launcher or '∅'}")

    env_added, env_removed = _set_delta(before.get("env_keys"), after.get("env_keys"))
    if env_added:
        bits.append(f"env: +{', '.join(env_added[:3])}")
    if env_removed:
        bits.append(f"env: -{', '.join(env_removed[:3])}")

    cap_added, cap_removed = _set_delta(before.get("capabilities"), after.get("capabilities"))
    cap_added = [_CAP_LABELS.get(c.lower(), c) for c in cap_added]
    cap_removed = [_CAP_LABELS.get(c.lower(), c) for c in cap_removed]
    if cap_added:
        bits.append(f"capabilities: +{', '.join(cap_added[:3])}")
    if cap_removed:
        bits.append(f"capabilities: -{', '.join(cap_removed[:3])}")

    old_pin = _pin_bit(before)
    new_pin = _pin_bit(after)
    if old_pin != new_pin:
        bits.append(f"pin: {old_pin or '∅'} → {new_pin or '∅'}")

    if not bits:
        bits.append("fields changed")
    return f'{prefix} {kind} "{name}" · ' + " · ".join(bits)


def removed_card(record: dict[str, Any], *, prefix: str = "-") -> str:
    kind = kind_label(record.get("kind"))
    name = str(record.get("name") or record.get("id") or "?").strip()
    return f'{prefix} {kind} "{name}" · removed'


def _is_renderable(record: dict[str, Any]) -> bool:
    return kind_label(record.get("kind")) not in _NOISE_KINDS


def delta_cards(delta: dict[str, Any] | None, *, limit: int = 3) -> list[str]:
    """Changed (old → new) first, then additions, then removals."""
    if not isinstance(delta, dict):
        return []
    changes = delta.get("changes") or {}
    cards: list[str] = []
    for item in changes.get("changed") or []:
        if str(item.get("change_class") or "") == "representation":
            continue
        if not _is_renderable(item.get("after") or item.get("before") or {}):
            continue
        cards.append(changed_card(item))
    for record in changes.get("added") or []:
        if _is_renderable(record):
            cards.append(record_card(record))
    for record in changes.get("removed") or []:
        if _is_renderable(record):
            cards.append(removed_card(record))
    for name in changes.get("mcp_tools_added") or []:
        cards.append(f'+ mcp tool "{name}" · pin added · publisher NOT VERIFIED')
    for name in changes.get("mcp_tools_removed") or []:
        cards.append(f'- mcp tool "{name}" · pin removed')
    for name in changes.get("mcp_tools_changed") or []:
        cards.append(f'~ mcp tool "{name}" · pin digest changed')
    return cards[:limit]


def count_cards(delta: dict[str, Any] | None) -> int:
    if not isinstance(delta, dict):
        return 0
    changes = delta.get("changes") or {}
    total = 0
    for key in ("added", "removed"):
        total += sum(1 for record in (changes.get(key) or []) if _is_renderable(record))
    for item in changes.get("changed") or []:
        if str(item.get("change_class") or "") == "representation":
            continue
        if _is_renderable(item.get("after") or item.get("before") or {}):
            total += 1
    for key in ("mcp_tools_added", "mcp_tools_removed", "mcp_tools_changed"):
        total += len(changes.get(key) or [])
    return total
