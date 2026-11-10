from __future__ import annotations

from pathlib import Path
from typing import Any

from authdiff.inventory.adapters.workflow_signals import workflow_text_has_agent_step
from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.limits import CollectorLimits


def discover_plugins(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in select_files(
        files,
        lambda p: (
            p.name in {"plugin.json", "plugin.yaml", "plugin.yml", ".cursor-plugin"}
            or (p.name == "package.json" and "plugin" in p.parent.name.lower())
        ),
    ):
        raw = safe_read_text(path, root=root, limits=limits, events=events, adapter="plugins")
        if raw is None:
            continue
        rel = path.relative_to(root).as_posix()
        results.append(
            {
                "name": path.parent.name if path.name.startswith("package") else path.stem,
                "type": "Plugin / Connector",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "plugins",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "priority_hints": ["publisher_and_scopes_manual_review"],
            }
        )
    return results


def discover_subagents(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in select_files(
        files,
        lambda p: (
            (
                ("agents" in p.parts or "subagents" in p.parts)
                and p.suffix in {".md", ".json", ".yaml", ".yml"}
                and p.name.lower() not in {"readme.md", "agents.md"}
            )
            or p.name in {"subagents.json", "agents.json"}
        ),
    ):
        raw = safe_read_text(path, root=root, limits=limits, events=events, adapter="subagents")
        if raw is None:
            continue
        rel = path.relative_to(root).as_posix()
        hints: list[str] = []
        lowered = raw.lower()
        if any(token in lowered for token in ("inherit", "permission", "tools", "mcp")):
            hints.append("delegation_or_permission_review")
        results.append(
            {
                "name": path.stem,
                "type": "Subagent",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "subagents",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "priority_hints": hints,
            }
        )
    return results


def discover_automations(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in select_files(
        files,
        lambda p: (
            p.name in {"automations.json", "automation.yaml", "automation.yml"}
            # GitHub Actions workflows are owned by discover_github_workflows
            # (type "CI Workflow") — do not double-register them here.
            or ("automations" in p.parts and p.suffix in {".json", ".yaml", ".yml", ".md"})
        ),
    ):
        raw = safe_read_text(path, root=root, limits=limits, events=events, adapter="automations")
        if raw is None:
            continue
        rel = path.relative_to(root).as_posix()
        hints: list[str] = []
        lowered = raw.lower()
        if "webhook" in lowered:
            hints.append("webhook_trigger")
        if any(token in lowered for token in ("cron", "schedule", "on:")):
            hints.append("scheduled_or_event_trigger")
        if any(token in lowered for token in ("secret", "token", "password")):
            hints.append("credential_reference")
        if workflow_text_has_agent_step(raw):
            hints.append("agent_related_step")
        results.append(
            {
                "name": path.stem,
                "type": "Automation / Workflow",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "automations",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "priority_hints": hints,
            }
        )
    return results
