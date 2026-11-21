"""Git identity + ecosystem-graph seed for scans.

Product ``security.engine`` imports ``resolve_git_commit`` and
``inventory_to_graph`` from this module. Not a second CLI surface.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from auctelis.inventory.collector import InventoryResult

_GIT = shutil.which("git")


def resolve_git_commit(root: Path) -> str | None:
    if not _GIT:
        return None
    try:
        # Fixed git argv, no shell, target root passed as cwd.
        proc = subprocess.run(  # nosec B603
            [_GIT, "rev-parse", "HEAD"],
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
