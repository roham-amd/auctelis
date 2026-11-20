from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auctelis.inventory.hints import (
    DOWNLOAD_EXEC_RE,
    HIDDEN_UNICODE_RE,
    INSTRUCTION_ABUSE_MARKERS,
    extract_url_hosts_from_command,
    permission_bypass_hint,
)
from auctelis.inventory.io import safe_read_text, select_files
from auctelis.inventory.limits import CollectorLimits

_CARD_NAMES = {"agent-card.json", "agent_card.json"}
_RULE_FILE_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CODEX.md",
    ".cursorrules",
    ".windsurfrules",
    ".clinerules",
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
    if HIDDEN_UNICODE_RE.search(raw):
        hints.append("hidden_unicode_in_instructions")
    if any(marker in lowered for marker in INSTRUCTION_ABUSE_MARKERS):
        hints.append("instruction_abuse_content")
    if "http://" in lowered or "https://" in lowered:
        hints.append("external_url_reference")
    if DOWNLOAD_EXEC_RE.search(raw) or any(
        token in lowered for token in ("curl ", "wget ", "| sh", "| bash")
    ):
        hints.append("download_and_execute")
    if permission_bypass_hint(raw):
        hints.append("permission_bypass_flag")
    return hints


def _instruction_record(
    *,
    name: str,
    kind: str,
    rel: str,
    raw: str,
) -> dict[str, Any]:
    destinations = extract_url_hosts_from_command(raw)
    return {
        "name": name,
        "type": kind,
        "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
        "repository_path": rel,
        "adapter": "instruction_rules",
        "adapter_maturity": "SUPPORTED",
        "discovery_status": "IDENTIFIED",
        "instruction_content_present": True,
        "priority_hints": _instruction_hints(raw),
        "destinations": destinations,
        "prose_inferred": True,
        "evidence_strength": "INFERRED_HINT",
    }


def _is_claude_command(path: Path) -> bool:
    """Claude Code slash-commands: ``.claude/commands/**/*.md``."""
    parts = [p.lower() for p in path.parts]
    if path.suffix.lower() != ".md":
        return False
    for i, part in enumerate(parts[:-1]):
        if part == ".claude" and i + 1 < len(parts) and parts[i + 1] == "commands":
            return True
    return False


def _under_dir(path: Path, *markers: str) -> bool:
    """True when ``markers`` appear as consecutive path parts (case-insensitive)."""
    parts = [p.lower() for p in path.parts]
    want = [m.lower() for m in markers]
    n = len(want)
    return any(parts[i : i + n] == want for i in range(len(parts) - n + 1))


def _is_instruction_file(path: Path, root: Path) -> bool:
    name = path.name
    if name in _RULE_FILE_NAMES:
        return True
    if _is_claude_command(path):
        return True
    rel = path.relative_to(root).as_posix().lower()
    if rel in {
        ".github/copilot-instructions.md",
        ".gemini/gemini.md",
    }:
        return True
    # GitHub Copilot custom instructions (watched by Action path_filter).
    if rel.startswith(".github/instructions/") and path.suffix.lower() in {
        ".md",
        ".txt",
    }:
        return True
    # Windsurf / Cline rule directories (2026 layouts).
    if path.is_file() and (
        _under_dir(path, ".windsurf", "rules")
        or _under_dir(path, ".clinerules")
        or (path.parent.name.lower() == ".clinerules")
    ):
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
            results.append(
                _instruction_record(
                    name=path.name,
                    kind="Rule / instruction file",
                    rel=rel,
                    raw=raw,
                )
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
        kind = "Claude slash command" if _is_claude_command(path) else "Rule / instruction file"
        results.append(
            _instruction_record(
                name=path.stem if _is_claude_command(path) else path.name,
                kind=kind,
                rel=rel,
                raw=raw,
            )
        )
    return results
