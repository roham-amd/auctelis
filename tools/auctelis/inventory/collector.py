"""Passive inventory collector — orchestrates adapters; no surface-specific logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auctelis.inventory.adapters.registry import DISCOVERY_ADAPTERS
from auctelis.inventory.coverage import summarize_coverage
from auctelis.inventory.io import iter_repo_files
from auctelis.inventory.limits import CollectorLimits
from auctelis.inventory.types import (
    ComponentRecord,
    DiscoveryAdapter,
    ParserEvent,
    assign_component_ids,
)
from auctelis.versioning import product_version

INVENTORY_VERSION = product_version()


@dataclass(slots=True)
class InventoryResult:
    repository_path: str
    collected_at_utc: str
    limits: dict[str, int]
    tree_summary: dict[str, Any]
    components: list[ComponentRecord] = field(default_factory=list)
    parser_events: list[ParserEvent] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    mode: str = "passive_read_only"


def collect_inventory(
    target: Path,
    *,
    limits: CollectorLimits | None = None,
    adapters: tuple[DiscoveryAdapter, ...] | None = None,
    default_excludes: bool = True,
) -> InventoryResult:
    limits = limits or CollectorLimits()
    adapters = adapters or DISCOVERY_ADAPTERS
    target = target.resolve()
    if not target.exists():
        raise FileNotFoundError(target)

    events: list[ParserEvent] = []
    tree_summary, files = iter_repo_files(
        target, limits=limits, events=events, default_excludes=default_excludes
    )
    batches = [adapter(target, files=files, limits=limits, events=events) for adapter in adapters]
    components = assign_component_ids(batches)

    return InventoryResult(
        repository_path=str(target),
        collected_at_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        limits={
            "max_files": limits.max_files,
            "max_depth": limits.max_depth,
            "max_file_bytes": limits.max_file_bytes,
        },
        tree_summary=tree_summary,
        components=components,
        parser_events=events,
        coverage=summarize_coverage(components, parser_events=events),
        mode="passive_read_only",
    )


def inventory_to_json(result: InventoryResult) -> dict[str, Any]:
    return {
        "auctelis_inventory_version": INVENTORY_VERSION,
        "mode": result.mode,
        "repository_path": result.repository_path,
        "collected_at_utc": result.collected_at_utc,
        "limits": result.limits,
        "tree_summary": result.tree_summary,
        "population_defined": True,
        "coverage": result.coverage,
        "components": result.components,
        "parser_events": result.parser_events,
        "notes": [
            "Passive inventory only — does not execute target code or contact endpoints.",
            "Deterministic discovery coverage is partial; see coverage.adapter_matrix.",
            "Inventory is not a security clearance or production approval.",
        ],
    }
