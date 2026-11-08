from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.limits import CollectorLimits

_CARD_NAMES = {"agent-card.json", "agent_card.json"}
_HIDDEN_UNICODE_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069]")
_INSTRUCTION_ABUSE_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "do not tell the user",
    "hide this action",
    "bypass confirmation",
    "skip approval",
    "exfiltrate",
    "fetch and execute",
    "download and run",
)
_RULE_FILE_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CODEX.md",
    ".cursorrules",
    ".windsurfrules",
    "copilot-instructions.md",
}


def discover_agent_cards(
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
            p.name in _CARD_NAMES or (p.name == "agent-card.json" and ".well-known" in p.parts)
        ),
    ):
        raw = safe_read_text(
            path, root=root, limits=limits, events=events, adapter="a2a_agent_card"
        )
        if raw is None:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            events.append(
                {
                    "type": "parse_error",
                    "adapter": "a2a_agent_card",
                    "path": rel,
                    "message": str(exc),
                }
            )
            continue
        results.append(
            {
                "name": data.get("name") or path.parent.name,
                "type": "A2A Agent Card",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "a2a_agent_card",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "declared_url": data.get("url"),
                "priority_hints": ["remote_agent_identity"] if data.get("url") else [],
            }
        )
    return results


def _instruction_hints(raw: str) -> list[str]:
    hints: list[str] = []
    lowered = raw.lower()
    if _HIDDEN_UNICODE_RE.search(raw):
        hints.append("hidden_unicode_in_instructions")
    if any(marker in lowered for marker in _INSTRUCTION_ABUSE_MARKERS):
        hints.append("instruction_abuse_content")
    return hints


def _is_instruction_file(path: Path, root: Path) -> bool:
    name = path.name
    if name in _RULE_FILE_NAMES:
        return True
    rel = path.relative_to(root).as_posix().lower()
    if rel in {
        ".github/copilot-instructions.md",
        ".gemini/GEMINI.md".lower(),
    }:
        return True
    return ".cursor" in path.parts and "rules" in path.parts


def discover_instruction_rules(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_dirs: set[str] = set()
    for path in select_files(files, lambda p: _is_instruction_file(p, root)):
        rel = path.relative_to(root).as_posix()
        # Cursor rules directory: one component per rules dir, but still scan each file
        # for unicode/injection hints on the individual path when it's a leaf rule.
        if ".cursor" in path.parts and "rules" in path.parts and path.is_file():
            raw = safe_read_text(
                path, root=root, limits=limits, events=events, adapter="instruction_rules"
            )
            if raw is None:
                continue
            hints = _instruction_hints(raw)
            results.append(
                {
                    "name": path.name,
                    "type": "Rule / instruction file",
                    "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                    "repository_path": rel,
                    "adapter": "instruction_rules",
                    "adapter_maturity": "SUPPORTED",
                    "discovery_status": "IDENTIFIED",
                    "instruction_content_present": True,
                    "priority_hints": hints,
                }
            )
            rules_dir = None
            parts = path.relative_to(root).parts
            for i, part in enumerate(parts):
                if part == "rules" and i > 0 and parts[i - 1] == ".cursor":
                    rules_dir = "/".join(parts[: i + 1])
                    break
            if rules_dir and rules_dir not in seen_dirs:
                seen_dirs.add(rules_dir)
                results.append(
                    {
                        "name": "cursor-rules",
                        "type": "Rule pack",
                        "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                        "repository_path": rules_dir,
                        "adapter": "instruction_rules",
                        "adapter_maturity": "PARTIAL",
                        "discovery_status": "IDENTIFIED",
                        "priority_hints": [],
                    }
                )
            continue

        raw = safe_read_text(
            path, root=root, limits=limits, events=events, adapter="instruction_rules"
        )
        if raw is None:
            continue
        results.append(
            {
                "name": path.name,
                "type": "Rule / instruction file",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "instruction_rules",
                "adapter_maturity": "SUPPORTED",
                "discovery_status": "IDENTIFIED",
                "instruction_content_present": True,
                "priority_hints": _instruction_hints(raw),
            }
        )
    return results
