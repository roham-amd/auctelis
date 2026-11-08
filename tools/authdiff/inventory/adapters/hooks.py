from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from authdiff.inventory.hints import (
    download_and_execute_hint,
    execution_boundary_hint,
    hook_lifecycle_event_hint,
    permission_bypass_hint,
    pre_execution_lifecycle_hint,
)
from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.limits import CollectorLimits

_HOOK_NAMES = {"hooks.json", "hooks.yaml", "hooks.yml"}


def _lifecycle_hints(name: str, text: str) -> list[str]:
    blob = f"{name}\n{text}"
    hints: list[str] = []
    for maybe in (
        pre_execution_lifecycle_hint(blob),
        hook_lifecycle_event_hint(blob),
        execution_boundary_hint(blob),
        download_and_execute_hint(blob),
        permission_bypass_hint(blob),
    ):
        if maybe:
            hints.append(maybe)
    if "possible_execution_boundary" in hints or "download_and_execute" in hints:
        hints.append("inherits_host_identity")
    return list(dict.fromkeys(hints))


def discover_hooks(
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
            p.name in _HOOK_NAMES
            or (p.parent.name == "hooks" and p.suffix in {".json", ".md", ".py"})
        ),
    ):
        raw = safe_read_text(path, root=root, limits=limits, events=events, adapter="hooks")
        if raw is None:
            continue
        rel = path.relative_to(root).as_posix()
        hints = _lifecycle_hints(path.stem, raw)
        name = path.stem
        if path.suffix == ".json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                events.append(
                    {
                        "type": "parse_error",
                        "adapter": "hooks",
                        "path": rel,
                        "message": str(exc),
                    }
                )
                continue

            if isinstance(data, dict) and "hooks" in data and isinstance(data["hooks"], dict):
                for hook_name, hook_body in data["hooks"].items():
                    body_text = json.dumps(hook_body, default=str) if hook_body is not None else ""
                    item_hints = _lifecycle_hints(str(hook_name), body_text)
                    results.append(
                        {
                            "name": str(hook_name),
                            "type": "Hook",
                            "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                            "repository_path": rel,
                            "adapter": "hooks",
                            "adapter_maturity": "PARTIAL",
                            "discovery_status": "IDENTIFIED",
                            "priority_hints": list(dict.fromkeys(item_hints)),
                            "lifecycle_event": str(hook_name),
                            "authority_layer": "CONFIGURED",
                            "limitations": [
                                "Hook discovery does not prove the host loads this file.",
                                "Execution identity and environment inheritance stay NOT VERIFIED.",
                            ],
                        }
                    )
                continue

        results.append(
            {
                "name": name,
                "type": "Hook",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "hooks",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "priority_hints": list(dict.fromkeys(hints)),
                "authority_layer": "CONFIGURED",
                "limitations": [
                    "Hook discovery does not prove the host loads this file.",
                    "Execution identity and environment inheritance stay NOT VERIFIED.",
                ],
            }
        )
    return results
