"""Inventory domain types and discovery adapter contract."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from auctelis.inventory.limits import CollectorLimits

type ComponentRecord = dict[str, Any]
type ParserEvent = dict[str, Any]


class DiscoveryAdapter(Protocol):
    """Open/Closed: new surfaces register without changing the collector core."""

    def __call__(
        self,
        root: Path,
        *,
        files: list[Path],
        limits: CollectorLimits,
        events: list[ParserEvent],
    ) -> list[ComponentRecord]: ...


def assign_component_ids(
    batches: Sequence[Sequence[ComponentRecord]],
    *,
    start: int = 1,
) -> list[ComponentRecord]:
    components: list[ComponentRecord] = []
    seq = start
    for batch in batches:
        for item in batch:
            item["component_id"] = f"C-{seq:03d}"
            seq += 1
            components.append(item)
    return components
