"""Reach severity tiers for Authority Diff ranking and gate failure.

Tier 0 — silent / representation (body packaging, prose doc hosts alone)
Tier 1 — comment (network reach; never fails the required check alone)
Tier 2 — fail when enforcing (execute, secrets, approvals, new MCP/hook/CI)

Prose ``INFERRED_HINT`` evidence is capped at tier 1 so a style-guide link
cannot page the same as ``curl | sh``.
"""

from __future__ import annotations

from typing import Any

# Public tier constants.
TIER_SILENT = 0
TIER_COMMENT = 1
TIER_FAIL = 2

_CAP_TIER: dict[str, int] = {
    "modify_agent_instructions": TIER_SILENT,
    "access_network": TIER_COMMENT,
    "invoke_tools": TIER_FAIL,
    "execute": TIER_FAIL,
    "access_secrets": TIER_FAIL,
    "unattended_operation": TIER_FAIL,
    "modify_approvals": TIER_FAIL,
}

_ADDITION_FAIL_KINDS = {
    "MCP Server Registration",
    "Hook",
    "CI Workflow",
    "Workflow",
    "Host Settings",
    "Plugin",
    "Plugin / Connector",
    "Subagent",
}


def capability_tier(cap: str) -> int:
    return _CAP_TIER.get(str(cap or ""), TIER_COMMENT)


def _trusted_host(host: str, trusted: set[str]) -> bool:
    h = str(host or "").strip().lower().rstrip(".")
    if not h or not trusted:
        return False
    return h in trusted or any(h.endswith(f".{t}") for t in trusted)


def record_reach_tier(
    record: dict[str, Any],
    *,
    trusted_hosts: set[str] | None = None,
) -> int:
    """Highest reach tier implied by one authority record."""
    trusted = {h.lower() for h in (trusted_hosts or set()) if h}
    kind = str(record.get("kind") or "")
    evidence = str(record.get("evidence_strength") or "")
    caps = [str(c) for c in (record.get("capabilities") or [])]
    destinations = [str(d) for d in (record.get("destinations") or [])]
    launcher = str(record.get("launcher") or "")
    pin = str(record.get("pin_state") or "")

    tier = TIER_SILENT
    for cap in caps:
        tier = max(tier, capability_tier(cap))

    if kind in _ADDITION_FAIL_KINDS:
        tier = max(tier, TIER_FAIL)
    if launcher and pin in {"floating", "unknown", ""}:
        tier = max(tier, TIER_FAIL)
    if any(c in {"execute", "access_secrets", "modify_approvals"} for c in caps):
        tier = max(tier, TIER_FAIL)
    # Env credentials on a record are secret reach even when caps lag adapters.
    if record.get("env_keys"):
        tier = max(tier, TIER_FAIL)

    # Destinations alone: network comment tier, unless every host is trusted.
    if destinations:
        if trusted and all(_trusted_host(d, trusted) for d in destinations):
            tier = max(tier, TIER_SILENT)
        else:
            tier = max(tier, TIER_COMMENT)

    # Prose / inferred hints never alone escalate to fail — unless env/secrets
    # or execute capabilities are already present on the record.
    if (
        evidence == "INFERRED_HINT"
        and tier >= TIER_FAIL
        and not record.get("env_keys")
        and not any(c in {"execute", "access_secrets", "modify_approvals"} for c in caps)
    ):
        tier = TIER_COMMENT
    if (
        evidence == "INFERRED_HINT"
        and not record.get("env_keys")
        and set(caps)
        <= {
            "access_network",
            "modify_agent_instructions",
        }
    ):
        tier = min(tier, TIER_COMMENT)

    return tier


def expansion_reach_tier(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    trusted_hosts: set[str] | None = None,
) -> int:
    """Tier of *new* reach when a matched record expands."""
    trusted = {h.lower() for h in (trusted_hosts or set()) if h}
    before_caps = {str(c) for c in (before.get("capabilities") or [])}
    after_caps = {str(c) for c in (after.get("capabilities") or [])}
    added_caps = after_caps - before_caps
    before_dest = {str(d) for d in (before.get("destinations") or [])}
    after_dest = {str(d) for d in (after.get("destinations") or [])}
    added_dest = after_dest - before_dest
    before_env = {str(e) for e in (before.get("env_keys") or [])}
    after_env = {str(e) for e in (after.get("env_keys") or [])}
    added_env = after_env - before_env

    tier = TIER_SILENT
    for cap in added_caps:
        tier = max(tier, capability_tier(cap))
    if added_env:
        tier = max(tier, TIER_FAIL)
    if added_dest:
        if trusted and all(_trusted_host(d, trusted) for d in added_dest):
            pass
        else:
            tier = max(tier, TIER_COMMENT)

    evidence = str(after.get("evidence_strength") or "")
    # Doc-link / prose network alone stays comment (or silent if only instructions).
    if (
        evidence == "INFERRED_HINT"
        and added_caps <= {"access_network", "modify_agent_instructions"}
        and not (after.get("launcher") and not before.get("launcher"))
    ):
        tier = min(tier, TIER_COMMENT)
        if added_caps <= {"modify_agent_instructions"} and not added_dest:
            tier = TIER_SILENT
        elif added_caps <= {"access_network", "modify_agent_instructions"}:
            # Pure inferred host mention → silent when no execute/secrets.
            tier = TIER_SILENT if "execute" not in after_caps else TIER_COMMENT
    return tier


def delta_max_reach_tier(
    delta: dict[str, Any],
    *,
    trusted_hosts: set[str] | None = None,
) -> int:
    """Highest reach tier across an authority lock delta."""
    raw_changes = delta.get("changes")
    changes: dict[str, Any] = raw_changes if isinstance(raw_changes, dict) else {}
    tier = TIER_SILENT
    for rec in changes.get("added") or []:
        if isinstance(rec, dict):
            tier = max(tier, record_reach_tier(rec, trusted_hosts=trusted_hosts))
    for item in changes.get("changed") or []:
        if not isinstance(item, dict):
            continue
        klass = str(item.get("change_class") or "")
        before_raw, after_raw = item.get("before"), item.get("after")
        before: dict[str, Any] = before_raw if isinstance(before_raw, dict) else {}
        after: dict[str, Any] = after_raw if isinstance(after_raw, dict) else {}
        if klass in {"expansion", "mixed", "replacement"}:
            tier = max(
                tier,
                expansion_reach_tier(before, after, trusted_hosts=trusted_hosts),
            )
            if klass == "replacement":
                tier = max(tier, record_reach_tier(after, trusted_hosts=trusted_hosts))
    if changes.get("mcp_tools_added") or changes.get("mcp_tools_changed"):
        tier = max(tier, TIER_FAIL)
    raw_summary = delta.get("summary")
    summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
    if summary.get("policy_changed"):
        tier = max(tier, TIER_FAIL)
    return tier


def load_trusted_hosts(root: Any = None) -> set[str]:
    """Optional ``.auctelis/trusted-hosts`` (one host per line) or policy file."""
    hosts: set[str] = set()
    if root is None:
        return hosts
    from pathlib import Path

    path = Path(root) / ".auctelis" / "trusted-hosts"
    if not path.is_file():
        return hosts
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return hosts
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            hosts.add(line)
    return hosts
