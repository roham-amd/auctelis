"""Emit compositional authority relationships between discovered components.

Individual findings can look acceptable while combinations create material risk
(skill + MCP + hook, subagent + inherited credentials, etc.). Relationships are
evidence-backed graph links — still POTENTIAL until independently verified.
"""

from __future__ import annotations

from typing import Any

from auctelis.security.models import Relationship

# Host-local pairing kinds that commonly compose into authority paths.
_COMPOSITE_KINDS: tuple[tuple[str, str, str], ...] = (
    ("Skill", "MCP Server Registration", "skill_invokes_mcp"),
    ("Hook", "MCP Server Registration", "hook_invokes_mcp"),
    ("Hook", "Skill", "hook_invokes_skill"),
    ("Subagent", "MCP Server Registration", "subagent_inherits_mcp"),
    ("Subagent", "Skill", "subagent_inherits_skill"),
    ("Automation", "MCP Server Registration", "automation_invokes_mcp"),
    ("GitHub Workflow", "MCP Server Registration", "ci_invokes_mcp"),
    ("Agent Instructions", "MCP Server Registration", "instructions_enable_mcp"),
)


def _kind_bucket(kind: str) -> str:
    text = (kind or "").strip()
    for label in (
        "MCP Server Registration",
        "Skill",
        "Hook",
        "Plugin",
        "Subagent",
        "Automation",
        "GitHub Workflow",
        "Agent Instructions",
    ):
        if label.lower() in text.lower() or text.lower() in label.lower():
            return label
    return text


def emit_relationships(components: list[dict[str, Any]]) -> list[Relationship]:
    """Build co-host composite relationships from inventory components."""
    by_host: dict[str, list[dict[str, Any]]] = {}
    for comp in components:
        host = str(comp.get("host") or "repo").strip().lower() or "repo"
        by_host.setdefault(host, []).append(comp)

    out: list[Relationship] = []
    seen: set[str] = set()
    for _host, group in by_host.items():
        indexed: dict[str, list[dict[str, Any]]] = {}
        for comp in group:
            bucket = _kind_bucket(str(comp.get("kind") or ""))
            indexed.setdefault(bucket, []).append(comp)
        for left_kind, right_kind, rel_kind in _COMPOSITE_KINDS:
            lefts = indexed.get(left_kind) or []
            rights = indexed.get(right_kind) or []
            for left in lefts:
                for right in rights:
                    lid = str(left.get("component_id") or "")
                    rid = str(right.get("component_id") or "")
                    if not lid or not rid or lid == rid:
                        continue
                    key = f"{rel_kind}:{lid}:{rid}"
                    if key in seen:
                        continue
                    seen.add(key)
                    evidence = [
                        eid
                        for eid in (
                            f"E-INV-{lid}",
                            f"E-INV-{rid}",
                        )
                        if eid
                    ]
                    out.append(
                        Relationship(
                            relationship_id=f"R-{len(out) + 1:03d}",
                            kind=rel_kind,
                            from_component_id=lid,
                            to_component_id=rid,
                            evidence_ids=evidence,
                            status="POTENTIAL",
                        )
                    )
    return out
