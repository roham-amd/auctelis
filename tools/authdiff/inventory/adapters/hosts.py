"""Discover agent-host configuration surfaces (Cursor, Claude Code, …).

Emits Host components with **declared** configuration only. Never claims
effective host permissions from file presence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from authdiff.hosts.profiles import HOST_PROFILES
from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.limits import CollectorLimits


def _cursor_markers(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    if name in {".cursorrules", "agents.md"}:
        return True
    return bool(rel == ".cursor/mcp.json" or rel.startswith(".cursor/"))


def _claude_markers(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    if name in {"claude.md", ".mcp.json", ".claude.json"}:
        return True
    return bool(rel.startswith(".claude/"))


def _copilot_markers(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    if name == "copilot-instructions.md":
        return True
    return rel in {
        ".github/copilot-instructions.md",
    } or rel.startswith(".github/instructions/")


def _codex_markers(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    return name in {"codex.md", "config.toml"} or rel.startswith(".codex/")


def _gemini_markers(path: Path, root: Path) -> bool:
    name = path.name.lower()
    return name in {"gemini.md", ".gemini.md"} or ".gemini" in path.parts


def _windsurf_markers(path: Path, root: Path) -> bool:
    name = path.name.lower()
    return name in {".windsurfrules", "windsurfrules"} or "windsurf" in path.parts


def _zed_markers(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    return rel.startswith(".zed/") or rel.startswith(".config/zed/")


def _continue_markers(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    return rel.startswith(".continue/")


def _opencode_markers(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    return name == "opencode.json" or rel.startswith(".opencode/")


def discover_host_profiles(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return at most one component per detected host family."""
    found: dict[str, list[str]] = {
        "cursor": [],
        "claude-code": [],
        "github-copilot": [],
        "codex": [],
        "gemini": [],
        "windsurf": [],
        "zed": [],
        "continue": [],
        "opencode": [],
    }

    for path in select_files(files, lambda p: True):
        rel = path.relative_to(root).as_posix()
        if _cursor_markers(path, root):
            found["cursor"].append(rel)
        if _claude_markers(path, root):
            found["claude-code"].append(rel)
        if _copilot_markers(path, root):
            found["github-copilot"].append(rel)
        if _codex_markers(path, root):
            found["codex"].append(rel)
        if _gemini_markers(path, root):
            found["gemini"].append(rel)
        if _windsurf_markers(path, root):
            found["windsurf"].append(rel)
        if _zed_markers(path, root):
            found["zed"].append(rel)
        if _continue_markers(path, root):
            found["continue"].append(rel)
        if _opencode_markers(path, root):
            found["opencode"].append(rel)
        # Bound memory: do not keep unbounded path lists.
        for key in found:
            if len(found[key]) > 20:
                found[key] = found[key][:20]

    results: list[dict[str, Any]] = []
    for host_id, paths in found.items():
        if not paths:
            continue
        profile = HOST_PROFILES.get(host_id)
        if profile is None:
            continue
        # Touch one file so limits/events stay consistent with other adapters.
        sample = root / paths[0]
        if sample.is_file():
            safe_read_text(sample, root=root, limits=limits, events=events, adapter="host_profiles")
        results.append(
            {
                "name": profile.display_name,
                "type": "Agent Host",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": paths[0],
                "adapter": "host_profiles",
                "adapter_maturity": profile.support,
                "discovery_status": "IDENTIFIED",
                "host_id": host_id,
                "permission_scope": "DECLARED_ONLY",
                "observed_config_paths": paths,
                "priority_hints": ["host_declared_configuration"],
                "limitations": list(profile.limitations),
                "effective_permissions": "NOT VERIFIED",
            }
        )
    return results
