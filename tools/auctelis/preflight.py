"""Git identity + ecosystem-graph seed for scans.

Product path uses ``resolve_git_commit`` and ``inventory_to_graph`` from
``security.engine``. The ``run_preflight`` / markdown helpers are maintainer
and test utilities only — not a second product surface.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from auctelis.inventory.collector import InventoryResult


def resolve_git_commit(root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def _node_kind_for_component(comp: dict[str, Any]) -> str:
    ctype = str(comp.get("type") or "").lower()
    mapping = (
        ("skill", "Skill"),
        ("mcp server registration", "McpClient"),
        ("mcp server implementation", "McpServer"),
        ("mcp", "McpServer"),
        ("plugin", "Plugin"),
        ("hook", "Hook"),
        ("subagent", "Agent"),
        ("automation", "Automation"),
        ("ci workflow", "Workflow"),
        ("workflow", "Workflow"),
        ("a2a", "A2APeer"),
        ("rule", "Policy"),
        ("instruction", "Policy"),
    )
    for needle, kind in mapping:
        if needle in ctype:
            return kind
    return "Package"


def inventory_to_graph(
    result: InventoryResult,
    *,
    commit: str | None = None,
    audit_id: str = "preflight",
) -> dict[str, Any]:
    """Build a schema-valid structural graph seed from inventory (not attack-path proof)."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    host_node = "N-host"
    inv_evidence = "E-INV"
    nodes.append(
        {
            "node_id": host_node,
            "kind": "AgentHost",
            "label": Path(result.repository_path).name,
            "verification_state": "INFERRED",
            "evidence_ids": [inv_evidence],
        }
    )
    for idx, comp in enumerate(result.components, start=1):
        node_id = f"N-{idx:03d}"
        nodes.append(
            {
                "node_id": node_id,
                "kind": _node_kind_for_component(comp),
                "label": str(comp.get("name") or node_id),
                "component_id": comp.get("component_id"),
                "verification_state": "INFERRED",
                "evidence_ids": [inv_evidence],
            }
        )
        edges.append(
            {
                "edge_id": f"E-{idx:03d}",
                "kind": "loads",
                "from_node_id": host_node,
                "to_node_id": node_id,
                "direction": "directed",
                "verification_state": "INFERRED",
                "evidence_ids": [inv_evidence],
                "limitations": [
                    "Structural inventory edge only; host binding not independently verified.",
                    f"source_path={comp.get('repository_path')}",
                ],
            }
        )
    return {
        "graph_version": "1.0",
        "audit_id": audit_id,
        "scope": {
            "repository": result.repository_path,
            "audited_commit": commit,
            "tree_sha": None,
        },
        "nodes": nodes,
        "edges": edges,
        "attack_paths": [],
        "limitations": [
            "Preflight/audit graph is structural inventory only — not an attack-path proof.",
            "All edges use synthetic evidence id E-INV from deterministic discovery.",
            "Deep audit must replace INFERRED edges with CONFIRMED evidence where claimed.",
        ],
    }


def build_audit_context_md(result: InventoryResult, *, commit: str | None) -> str:
    coverage = result.coverage or {}
    counts = coverage.get("component_counts_by_type") or {}
    lines = [
        "# auctelis — Audit Context (Preflight)",
        "",
        f"- Repository: `{result.repository_path}`",
        f"- Commit: `{commit or 'unknown'}`",
        f"- Collected at (UTC): `{result.collected_at_utc}`",
        f"- Mode: `{result.mode}`",
        "",
        "## Discovered components",
        "",
    ]
    if counts:
        for name, count in sorted(counts.items()):
            lines.append(f"- {name}: **{count}**")
    else:
        lines.append("- None discovered by deterministic adapters.")

    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Deterministically discovered: **{coverage.get('deterministically_discovered', 0)}**",
            f"- By maturity: `{json.dumps(coverage.get('component_counts_by_maturity') or {})}`",
            "",
            "### Manual / unsupported families",
            "",
        ]
    )
    for family in coverage.get("manual_review_families") or []:
        lines.append(f"- {family}")

    lines.extend(["", "## High-priority review areas", ""])
    priority = coverage.get("high_priority_review_areas") or []
    if not priority:
        lines.append("- None flagged by static hints (still not a clean bill of health).")
    else:
        for item in priority:
            hints = ", ".join(item.get("hints") or [])
            lines.append(
                f"- `[!]` {item.get('type')} `{item.get('name')}` "
                f"({item.get('repository_path')}): {hints}"
            )

    lines.extend(["", "## NOT VERIFIED", ""])
    for item in coverage.get("not_verified") or []:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Next steps for AI audit agent",
            "",
            "1. Use this inventory; do not claim full ecosystem discovery beyond adapter coverage.",
            "2. Review high-priority components with `auctelis scan` / `auctelis lock`.",
            "3. Produce findings via `auctelis scan`; validate reports with `auctelis-dev validate report`.",
            "4. Keep runtime, publisher identity, and host effective permissions as NOT VERIFIED unless new evidence is supplied.",
            "",
            "## Safety",
            "",
            "- Passive / read-only: do not install dependencies, run target code, or contact MCP/production endpoints.",
            "- This preflight is **not** a security clearance.",
            "",
        ]
    )
    return "\n".join(lines)


def render_preflight_text(result: InventoryResult, *, commit: str | None, out_dir: Path) -> str:
    coverage = result.coverage or {}
    counts = coverage.get("component_counts_by_type") or {}
    lines = [
        "auctelis — Agent Ecosystem Preflight",
        f"Repository: {Path(result.repository_path).name}",
        f"Commit: {commit or 'unknown'}",
        "",
        "DISCOVERED COMPONENTS",
    ]
    if counts:
        width = max(len(k) for k in counts) + 2
        for name, count in sorted(counts.items()):
            lines.append(f"  {name.ljust(width)}{count}")
    else:
        lines.append("  (none)")

    lines.extend(
        [
            "",
            "COVERAGE",
            f"  Deterministically discovered     {coverage.get('deterministically_discovered', 0)}",
            f"  Maturity breakdown               {coverage.get('component_counts_by_maturity')}",
            "",
            "HIGH-PRIORITY REVIEW AREAS",
        ]
    )
    priority = coverage.get("high_priority_review_areas") or []
    if not priority:
        lines.append("  (none flagged by static hints)")
    else:
        for item in priority[:15]:
            hints = ", ".join(item.get("hints") or [])
            lines.append(f"  [!] {item.get('type')}: {item.get('name')} — {hints}")

    lines.extend(["", "NOT VERIFIED"])
    for item in coverage.get("not_verified") or []:
        lines.append(f"  - {item}")

    lines.extend(
        [
            "",
            "OUTPUT",
            f"  {out_dir.as_posix()}/inventory.json",
            f"  {out_dir.as_posix()}/ecosystem-graph.json",
            f"  {out_dir.as_posix()}/audit-context.md",
            f"  {out_dir.as_posix()}/preflight-summary.md",
            "",
            "This is discovery + coverage, not a pass/fail security verdict.",
        ]
    )
    return "\n".join(lines)


def run_preflight(target: Path, *, output_dir: Path | None = None) -> dict[str, Any]:
    """Write inventory + graph + context for a target (legacy preflight path)."""
    from auctelis.inventory.collector import collect_inventory
    from auctelis.jsonio import write_json, write_text

    target = target.resolve()
    out = (output_dir or (target / "auctelis-out")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    inv = collect_inventory(target)
    commit = resolve_git_commit(target)
    graph = inventory_to_graph(inv)
    from auctelis.inventory.collector import inventory_to_json

    write_json(out / "inventory.json", inventory_to_json(inv))
    write_json(out / "ecosystem-graph.json", graph)
    context = build_audit_context_md(inv, commit=commit)
    write_text(out / "audit-context.md", context)
    write_text(out / "preflight-summary.md", render_preflight_text(inv, commit=commit, out_dir=out))
    return {
        "component_count": len(inv.components),
        "commit": commit,
        "output_dir": str(out),
        "summary": context,
    }
