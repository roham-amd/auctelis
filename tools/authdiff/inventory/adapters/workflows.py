"""Discover CI / automation workflow files as authority-bearing surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from authdiff.inventory.adapters.workflow_signals import analyze_github_workflow
from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.limits import CollectorLimits


def discover_github_workflows(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def is_workflow(path: Path) -> bool:
        parts = {p.lower() for p in path.parts}
        name = path.name.lower()
        return bool(
            name.endswith((".yml", ".yaml")) and ".github" in parts and "workflows" in parts
        )

    for path in select_files(files, is_workflow):
        raw = safe_read_text(
            path, root=root, limits=limits, events=events, adapter="github_workflows"
        )
        if raw is None:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        hints = analyze_github_workflow(raw)

        results.append(
            {
                "name": path.stem,
                "type": "CI Workflow",
                "reference_kind": "LOCAL_IMPLEMENTATION",
                "repository_path": rel,
                "adapter": "github_workflows",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "priority_hints": hints,
            }
        )
    return results
