from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from auctelis.semantic import SemanticIssue, issue


@dataclass
class PathResult:
    path_id: str
    node_ids: list[str]
    edge_ids: list[str]
    summary: str


@dataclass
class GraphSemanticResult:
    ok: bool
    issues: list[SemanticIssue] = field(default_factory=list)
    paths: list[PathResult] = field(default_factory=list)


def validate_graph_semantics(graph: dict[str, Any]) -> GraphSemanticResult:
    issues: list[SemanticIssue] = []
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    node_ids = {n["node_id"] for n in nodes if n.get("node_id")}
    edge_ids = {e["edge_id"] for e in edges if e.get("edge_id")}

    if len(node_ids) != len(nodes):
        issues.append(issue("DUPLICATE_ID", "node_id values must be unique", "nodes"))

    for idx, edge in enumerate(edges):
        for ref_key, label in (
            ("from_node_id", "from"),
            ("to_node_id", "to"),
        ):
            ref = edge.get(ref_key)
            if ref and ref not in node_ids:
                issues.append(
                    issue(
                        "DANGLING_NODE_REF",
                        f"edge {edge.get('edge_id')} {label} references unknown node {ref}",
                        f"edges[{idx}]",
                    )
                )
        for eid in edge.get("evidence_ids") or []:
            if not eid:
                issues.append(
                    issue(
                        "INVALID_EVIDENCE", "edge evidence_ids must be non-empty", f"edges[{idx}]"
                    )
                )

    for ap in graph.get("attack_paths") or []:
        for eid in ap.get("edge_ids") or []:
            if eid not in edge_ids:
                issues.append(
                    issue(
                        "DANGLING_EDGE_REF",
                        f"path {ap.get('path_id')} references unknown edge {eid}",
                        "attack_paths",
                    )
                )

    return GraphSemanticResult(ok=len(issues) == 0, issues=issues)


def find_paths(
    graph: dict[str, Any],
    *,
    start_kinds: set[str],
    end_kinds: set[str],
    max_depth: int = 12,
) -> list[PathResult]:
    nodes = {n["node_id"]: n for n in graph.get("nodes") or []}
    adj: dict[str, list[tuple[str, str]]] = {}
    for edge in graph.get("edges") or []:
        if edge.get("direction") == "bidirectional":
            continue
        fr, to, eid = edge.get("from_node_id"), edge.get("to_node_id"), edge.get("edge_id")
        if fr and to and eid:
            adj.setdefault(fr, []).append((to, eid))

    results: list[PathResult] = []
    starts = [nid for nid, n in nodes.items() if n.get("kind") in start_kinds]
    ends = {nid for nid, n in nodes.items() if n.get("kind") in end_kinds}

    pid = 0
    for start in starts:
        queue: deque[tuple[str, list[str], list[str]]] = deque([(start, [start], [])])
        seen_paths: set[tuple[str, ...]] = set()
        while queue:
            node, npath, epath = queue.popleft()
            if len(npath) > max_depth:
                continue
            if node in ends and len(epath) > 0:
                key = tuple(npath)
                if key not in seen_paths:
                    seen_paths.add(key)
                    pid += 1
                    results.append(
                        PathResult(
                            path_id=f"P-auto-{pid:03d}",
                            node_ids=npath,
                            edge_ids=epath,
                            summary=f"Path from {nodes[start]['kind']} to {nodes[node]['kind']} "
                            f"({len(epath)} edges)",
                        )
                    )
                continue
            for nxt, eid in adj.get(node, []):
                if nxt in npath:
                    continue
                queue.append((nxt, [*npath, nxt], [*epath, eid]))
    return results


DEFAULT_UNTRUSTED_TO_EXTERNAL = (
    {"Skill", "DataAsset"},
    {"ExternalRecipient", "McpServer", "Tool"},
)
