from __future__ import annotations

from typing import Any


def diff_reports(base: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    base_components = {
        c["component_id"]: c for c in base.get("components") or [] if c.get("component_id")
    }
    target_components = {
        c["component_id"]: c for c in target.get("components") or [] if c.get("component_id")
    }
    base_findings = {f["finding_id"]: f for f in base.get("findings") or [] if f.get("finding_id")}
    target_findings = {
        f["finding_id"]: f for f in target.get("findings") or [] if f.get("finding_id")
    }

    comp_added = sorted(set(target_components) - set(base_components))
    comp_removed = sorted(set(base_components) - set(target_components))
    find_added = sorted(set(target_findings) - set(base_findings))
    find_removed = sorted(set(base_findings) - set(target_findings))

    find_changed: list[dict[str, Any]] = []
    for fid in sorted(set(base_findings) & set(target_findings)):
        b, t = base_findings[fid], target_findings[fid]
        fields = []
        for key in ("severity", "evidence_label", "title"):
            if b.get(key) != t.get(key):
                fields.append(key)
        if fields:
            find_changed.append({"finding_id": fid, "fields": fields})

    return {
        "diff_version": "1.0",
        "base": {
            "repository": base.get("repository"),
            "audited_commit": base.get("audited_commit"),
        },
        "target": {
            "repository": target.get("repository"),
            "audited_commit": target.get("audited_commit"),
        },
        "summary": {
            "components_added": len(comp_added),
            "components_removed": len(comp_removed),
            "findings_added": len(find_added),
            "findings_removed": len(find_removed),
            "findings_changed": len(find_changed),
        },
        "changes": {
            "components_added": comp_added,
            "components_removed": comp_removed,
            "findings_added": find_added,
            "findings_removed": find_removed,
            "findings_changed": find_changed,
        },
        "limitations": [
            "Structural ID diff only; graph edges and evidence spans are not compared in v1.0 diff.",
        ],
    }


def diff_graphs(base: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    def edge_key(e: dict) -> str:
        return e.get("edge_id") or f"{e.get('from_node_id')}->{e.get('to_node_id')}:{e.get('kind')}"

    base_edges = {edge_key(e): e for e in base.get("edges") or []}
    target_edges = {edge_key(e): e for e in target.get("edges") or []}
    added = sorted(set(target_edges) - set(base_edges))
    removed = sorted(set(base_edges) - set(target_edges))
    return {
        "diff_version": "1.0",
        "edges_added": added,
        "edges_removed": removed,
        "limitations": ["Graph node attribute changes not compared in this pilot."],
    }
