"""One-line authority cards for the terminal, session hook, and PR comment.

The product sentence is a declared-config diff:

    + mcp "linear" → mcp.linear.app · network · unpinned · publisher NOT VERIFIED

User-facing fields: name, destination (host or launcher), capability set,
env-key names, reach tier + reason, and evidence strength. Everything else in
the lock stays available to tooling but does not become the page.
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
    "plugin / connector": "plugin",
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
# Agent-host containers are inventory scaffolding, not sealable authority.
# Host Settings (permissions, bypass) MUST appear — they are the highest-risk class.
_NOISE_KINDS = {"agent host"}
_HIGHLIGHT_CAPS = {"network", "secrets", "execute", "tools", "approvals", "unattended"}
_POSTURE_LABELS = {
    "prompt": "prompt",
    "auto": "auto",
    "bypass": "bypassPermissions",
    "unknown": "unknown",
}


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
        host = _host_from(item) or (str(item).strip().lower() if "." in str(item) else "")
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


def _posture(record: dict[str, Any]) -> str:
    raw = str(record.get("approval_posture") or "").strip().lower()
    return _POSTURE_LABELS.get(raw, raw)


def _permission_allows(record: dict[str, Any]) -> list[str]:
    return [str(a) for a in (record.get("permission_allows") or []) if str(a).strip()]


def _env_keys(record: dict[str, Any], *, limit: int = 3) -> list[str]:
    """Secret *names* only — never values. Added cards must say why they matter."""
    return [str(k) for k in (record.get("env_keys") or []) if str(k).strip()][:limit]


def _tier_bit(
    record: dict[str, Any],
    *,
    trusted_hosts: set[str] | None = None,
) -> str:
    from auctelis.reach_tiers import reach_reason, record_reach_tier

    tier = record_reach_tier(record, trusted_hosts=trusted_hosts)
    if tier <= 0:
        return ""
    reason = reach_reason(record, trusted_hosts=trusted_hosts)
    return f"tier {tier} ({reason})"


def evidence_label(record: dict[str, Any]) -> str:
    """Evidence strength for cards / why — never invent LITERAL_CONFIG."""
    raw = str(record.get("evidence_strength") or "").strip().upper()
    if raw in {"LITERAL_CONFIG", "INFERRED_HINT", "NAME_MARKER"}:
        return raw
    return "INFERRED_HINT"


def _path_bit(record: dict[str, Any]) -> str:
    path = str(record.get("path") or "").replace("\\", "/")
    if not path:
        return ""
    return f" @ {_short(path, width=56)}"


def record_card(
    record: dict[str, Any],
    *,
    prefix: str = "+",
    trusted_hosts: set[str] | None = None,
) -> str:
    """Render one added/current authority record as a single card line."""
    kind = kind_label(record.get("kind"))
    name = str(record.get("name") or record.get("id") or "?").strip()
    path_bit = _path_bit(record)
    host = destination(record)
    launch = launcher(record)
    posture = _posture(record)
    allows = _permission_allows(record)
    env_keys = _env_keys(record)
    tier_bit = _tier_bit(record, trusted_hosts=trusted_hosts)
    evidence = evidence_label(record)

    # First-class permission-posture card for host settings / bypass.
    if kind == "host" or posture == "bypassPermissions" or allows:
        bits: list[str] = []
        if posture and posture != "unknown":
            bits.append(f"permissions: {posture}")
        if allows:
            shown = ", ".join(allows[:4])
            bits.append(f"+allow {shown}")
        caps = _capabilities(record)
        for cap in caps:
            if cap not in {"approvals", "unattended"} and cap not in bits:
                bits.append(cap)
        if host:
            bits.append(f"→ {host}")
        if env_keys:
            bits.append(f"env: {', '.join(env_keys)}")
        if tier_bit:
            bits.append(tier_bit)
        bits.append(_PUBLISHER)
        bits.append(evidence)
        return f'{prefix} {kind} "{name}"{path_bit} · ' + " · ".join(bits)

    bits = []
    target = ""
    if host:
        target = f" → {host}"
    elif launch:
        target = f" launcher {_short(launch)}"
    target += path_bit

    caps = _capabilities(record)
    bits.append(" · ".join(caps) if caps else "authority")
    pin = _pin_bit(record)
    if kind in _MCP_KINDS and pin:
        bits.append(pin)
    if env_keys:
        bits.append(f"env: {', '.join(env_keys)}")
    if tier_bit:
        bits.append(tier_bit)
    bits.append(_PUBLISHER)
    bits.append(evidence)
    return f'{prefix} {kind} "{name}"{target} · ' + " · ".join(bits)


def _hosts(record: dict[str, Any]) -> set[str]:
    hosts = {str(record.get("url_host") or "").strip().lower()}
    for item in record.get("destinations") or []:
        host = _host_from(item) or (str(item).strip().lower() if "." in str(item) else "")
        hosts.add(host)
    return {h for h in hosts if h}


def _set_delta(before: Any, after: Any) -> tuple[list[str], list[str]]:
    b = {str(x) for x in (before or []) if str(x)}
    a = {str(x) for x in (after or []) if str(x)}
    return sorted(a - b), sorted(b - a)


def changed_card(
    item: dict[str, Any],
    *,
    prefix: str = "~",
    trusted_hosts: set[str] | None = None,
) -> str:
    """Render an existing record whose authority fields changed (old → new)."""
    before = item.get("before") or {}
    after = item.get("after") or {}
    kind = kind_label(after.get("kind") or before.get("kind"))
    name = str(after.get("name") or before.get("name") or item.get("id") or "?").strip()
    path_bit = _path_bit(after if after.get("path") else before)
    bits: list[str] = []

    old_posture, new_posture = _posture(before), _posture(after)
    if old_posture != new_posture:
        bits.append(f"permissions: {old_posture or '∅'} → {new_posture or '∅'}")

    allow_added, allow_removed = _set_delta(
        before.get("permission_allows"), after.get("permission_allows")
    )
    if allow_added:
        bits.append(f"+allow {', '.join(allow_added[:3])}")
    if allow_removed:
        bits.append(f"-allow {', '.join(allow_removed[:3])}")

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

    if before.get("script_digest") != after.get("script_digest") and "body changed" not in " ".join(
        bits
    ):
        bits.append("body changed (digest; line diff not analyzed)")
    # Always name a concrete field — never a bare "fields changed".
    if not bits:
        changed_fields = []
        for field in (
            "approval_posture",
            "permission_allows",
            "destinations",
            "url_host",
            "launcher",
            "capabilities",
            "env_keys",
            "pin_state",
            "args_digest",
        ):
            if before.get(field) != after.get(field):
                changed_fields.append(field)
        if before.get("script_digest") != after.get("script_digest"):
            bits.append("body changed (digest; line diff not analyzed)")
        elif changed_fields:
            bits.append(f"{changed_fields[0]} changed")
        else:
            bits.append("record identity changed")
    tier_bit = _tier_bit(after if after else before, trusted_hosts=trusted_hosts)
    if tier_bit:
        bits.append(tier_bit)
    evidence = evidence_label(after if after else before)
    bits.append(evidence)
    return f'{prefix} {kind} "{name}"{path_bit} · ' + " · ".join(bits)


def removed_card(record: dict[str, Any], *, prefix: str = "-") -> str:
    kind = kind_label(record.get("kind"))
    name = str(record.get("name") or record.get("id") or "?").strip()
    path_bit = _path_bit(record)
    return f'{prefix} {kind} "{name}"{path_bit} · removed'


def _is_renderable(record: dict[str, Any]) -> bool:
    return kind_label(record.get("kind")) not in _NOISE_KINDS


def is_highlight_record(record: dict[str, Any]) -> bool:
    """True when the record introduces a new destination, executable, or secret.

    First-run screens show these first; host permission posture is always a highlight.
    """
    if not _is_renderable(record):
        return False
    if _posture(record) == "bypassPermissions":
        return True
    if _permission_allows(record):
        return True
    if destination(record):
        return True
    if launcher(record):
        return True
    caps = set(_capabilities(record))
    if caps & _HIGHLIGHT_CAPS:
        return True
    return bool(record.get("env_keys"))


def highlight_cards(
    records: list[dict[str, Any]] | None,
    *,
    limit: int | None = None,
) -> tuple[list[str], int, int]:
    """Return ``(cards, highlight_total, inventory_total)`` for a first-run screen.

    Every sealable (renderable) record is shown so seal never hides Host Settings.
    Highlights are listed first. ``limit=None`` means no truncation.
    """
    inventory = [r for r in (records or []) if _is_renderable(r)]
    highlights = [r for r in inventory if is_highlight_record(r)]
    remainder = [r for r in inventory if not is_highlight_record(r)]
    ordered = [*highlights, *remainder]
    shown = ordered if limit is None else ordered[: max(int(limit), 0)]
    cards = [record_card(r) for r in shown]
    return cards, len(highlights), len(inventory)


def sealable_records(records: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Records that appear on screen and may be sealed (excludes agent-host noise)."""
    return [r for r in (records or []) if _is_renderable(r)]


def why_record(record: dict[str, Any]) -> list[str]:
    """Exact file / field lines for ``auctelis why``."""
    kind = kind_label(record.get("kind"))
    name = str(record.get("name") or record.get("id") or "?").strip()
    path = str(record.get("path") or "").replace("\\", "/") or "(path unknown)"
    lines = [
        f'{kind} "{name}"',
        f"  path: {path}",
    ]
    posture = _posture(record)
    if posture and posture != "unknown":
        lines.append(f"  permissions: {posture}")
    allows = _permission_allows(record)
    if allows:
        lines.append(f"  allow: {', '.join(allows[:8])}")
    host = destination(record)
    if host:
        lines.append(f"  destination: {host}")
    launch = launcher(record)
    if launch:
        lines.append(f"  launcher: {launch}")
    caps = _capabilities(record)
    if caps:
        lines.append(f"  capabilities: {', '.join(caps)}")
    env = [str(x) for x in (record.get("env_keys") or []) if str(x)]
    if env:
        lines.append(f"  env_keys: {', '.join(env[:8])}")
    pin = _pin_bit(record)
    if pin:
        lines.append(f"  pin: {pin}")
    lines.append(f"  {_PUBLISHER}")
    evidence = evidence_label(record)
    lines.append(f"  evidence: {evidence} (declared config only; not runtime proof)")
    return lines


def find_records_by_name(
    records: list[dict[str, Any]] | None,
    query: str,
) -> list[dict[str, Any]]:
    needle = str(query or "").strip().lower()
    if not needle:
        return []
    out: list[dict[str, Any]] = []
    for record in records or []:
        name = str(record.get("name") or "").strip().lower()
        rid = str(record.get("id") or "").strip().lower()
        if needle == name or needle in name or needle in rid:
            out.append(record)
    return out


def _risk_score(record: dict[str, Any] | None) -> int:
    """Higher = show earlier when truncating PR cards."""
    if not isinstance(record, dict):
        return 0
    score = 0
    if _posture(record) == "bypassPermissions":
        score += 100
    caps = set(_capabilities(record))
    if caps & {"execute", "approvals", "unattended"}:
        score += 50
    if "secrets" in caps:
        score += 40
    if caps & {"network", "tools"}:
        score += 30
    if _pin_bit(record) == "unpinned":
        score += 20
    if record.get("env_keys"):
        score += 10
    return score


def _risk_summary(records: list[dict[str, Any]], *, hidden: int) -> str | None:
    if hidden <= 0:
        return None
    named: list[str] = []
    for record in records:
        name = str(record.get("name") or record.get("id") or "?").strip()
        bits: list[str] = []
        if _posture(record) == "bypassPermissions":
            bits.append("bypass")
        caps = set(_capabilities(record))
        if "execute" in caps:
            bits.append("execute")
        if "secrets" in caps:
            bits.append("secrets")
        if "network" in caps or destination(record):
            bits.append("network")
        if record.get("env_keys"):
            bits.append("env")
        if launcher(record):
            bits.append("launcher")
        reason = "/".join(bits) if bits else kind_label(record.get("kind"))
        named.append(f"{name} ({reason})")
    if named:
        shown = ", ".join(named[:4])
        extra = f", +{len(named) - 4}" if len(named) > 4 else ""
        return f"+{hidden} more: {shown}{extra}"
    return f"+{hidden} more"


def delta_cards(
    delta: dict[str, Any] | None,
    *,
    limit: int = 10,
    include_overflow_summary: bool = False,
    trusted_hosts: set[str] | None = None,
) -> list[str]:
    """Risk-ranked cards: bypass/execute/secrets before quieter additions."""
    if not isinstance(delta, dict):
        return []
    changes = delta.get("changes") or {}
    ranked: list[tuple[int, int, str, dict[str, Any] | None]] = []
    order = 0
    for item in changes.get("changed") or []:
        if str(item.get("change_class") or "") == "representation":
            continue
        after = item.get("after") or item.get("before") or {}
        if not _is_renderable(after):
            continue
        ranked.append(
            (
                _risk_score(after),
                order,
                changed_card(item, trusted_hosts=trusted_hosts),
                after,
            )
        )
        order += 1
    for record in changes.get("added") or []:
        if _is_renderable(record):
            ranked.append(
                (
                    _risk_score(record),
                    order,
                    record_card(record, trusted_hosts=trusted_hosts),
                    record,
                )
            )
            order += 1
    for record in changes.get("removed") or []:
        if _is_renderable(record):
            ranked.append((0, order, removed_card(record), record))
            order += 1
    for name in changes.get("mcp_tools_added") or []:
        ranked.append(
            (15, order, f'+ mcp tool "{name}" · pin added · publisher NOT VERIFIED', None)
        )
        order += 1
    for name in changes.get("mcp_tools_removed") or []:
        ranked.append((0, order, f'- mcp tool "{name}" · pin removed', None))
        order += 1
    for name in changes.get("mcp_tools_changed") or []:
        ranked.append((10, order, f'~ mcp tool "{name}" · pin digest changed', None))
        order += 1
    ranked.sort(key=lambda row: (-row[0], row[1]))
    shown = ranked[:limit]
    cards = [row[2] for row in shown]
    if include_overflow_summary and len(ranked) > limit:
        hidden_records = [row[3] for row in ranked[limit:] if isinstance(row[3], dict)]
        summary = _risk_summary(hidden_records, hidden=len(ranked) - limit)
        if summary:
            cards.append(summary)
    return cards


def _is_unpinned_mcp(record: dict[str, Any]) -> bool:
    if kind_label(record.get("kind")) != "mcp":
        return False
    pin = str(record.get("pin_state") or "").strip().lower()
    if pin in {"floating", "unknown", ""}:
        return True
    launch = launcher(record)
    return bool(launch) and pin not in {"pinned", "digest"}


def pin_suggestion(record: dict[str, Any]) -> str:
    """Concrete next step for a floating MCP launcher (names only, no network)."""
    launch = launcher(record).lower()
    if launch in {"npx", "bunx"}:
        return "pin the package: npx -y <pkg>@<exact-version>"
    if launch in {"uvx", "pipx"}:
        return "pin the package: <pkg>==<exact-version>"
    if launch in {"docker", "podman"}:
        return "pin the image: <image>@sha256:<digest>"
    if launch:
        return f"pin {launch} to an exact version or digest"
    return "prefer a versioned/signed endpoint, then reseal the lock"


def pin_report(records: list[dict[str, Any]] | None) -> dict[str, Any]:
    """MCP pin doctor: unpinned/floating servers and a concrete suggestion."""
    mcps = [r for r in (records or []) if kind_label(r.get("kind")) == "mcp"]
    items: list[dict[str, Any]] = []
    for record in mcps:
        if not _is_unpinned_mcp(record):
            continue
        items.append(
            {
                "name": str(record.get("name") or record.get("id") or "?"),
                "path": str(record.get("path") or ""),
                "launcher": launcher(record),
                "pin_state": str(record.get("pin_state") or "unknown"),
                "env_keys": _env_keys(record, limit=8),
                "suggestion": pin_suggestion(record),
            }
        )
    items.sort(key=lambda item: (item["name"], item["path"]))
    return {"total": len(mcps), "unpinned": len(items), "items": items}


def reach_snapshot(
    records: list[dict[str, Any]] | None,
    *,
    limit: int = 5,
    trusted_hosts: set[str] | None = None,
) -> dict[str, Any]:
    """Ranked reach summary for `auctelis check` (tiers + top cards)."""
    from auctelis.reach_tiers import reach_reason, record_reach_tier

    inventory = [r for r in (records or []) if _is_renderable(r)]
    tier_counts = {"tier0": 0, "tier1": 0, "tier2": 0}
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for record in inventory:
        tier = record_reach_tier(record, trusted_hosts=trusted_hosts)
        tier_counts[f"tier{min(tier, 2)}"] += 1
        scored.append((tier, _risk_score(record), record))
    scored.sort(
        key=lambda row: (
            -row[0],
            -row[1],
            str(row[2].get("name") or ""),
            str(row[2].get("path") or ""),
        )
    )
    top: list[dict[str, Any]] = []
    for tier, _score, record in scored[: max(int(limit or 0), 0)]:
        top.append(
            {
                "kind": kind_label(record.get("kind")),
                "name": str(record.get("name") or record.get("id") or "?"),
                "path": str(record.get("path") or ""),
                "tier": tier,
                "reason": reach_reason(record, trusted_hosts=trusted_hosts),
                "card": record_card(record, trusted_hosts=trusted_hosts),
            }
        )
    return {
        "total": len(inventory),
        "tier_counts": tier_counts,
        "top": top,
        "top_cards": [item["card"] for item in top],
    }
