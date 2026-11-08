"""Discover CI / automation workflow files as authority-bearing surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
        hints: list[str] = []
        lowered = raw.lower()
        if "permissions:" in lowered:
            hints.append("explicit_github_permissions_block")
        if "secrets." in lowered or "${{ secrets" in lowered:
            hints.append("secret_reference")
        if "pull_request_target" in lowered:
            hints.append("pull_request_target")
        if "workflow_dispatch" in lowered:
            hints.append("manual_dispatch")
        if any(tok in lowered for tok in ("curl ", "wget ", "pip install", "npm install")):
            hints.append("install_or_network_step_reference")
        agent_tokens = (
            "authdiff ",
            "authdiff",
            "claude",
            "cursor",
            "openai",
            "codex",
            "agent ",
            "mcp",
            "anthropic",
            "modelcontextprotocol",
        )
        if any(tok in lowered for tok in agent_tokens):
            hints.append("agent_related_step")
        if "pull_request_target" in lowered and "agent_related_step" in hints:
            hints.append("pull_request_target_with_agent")

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
