"""Host config discovery and staging for archived `watch` / `doctor` / `lock --home`.

Repo ``check`` / ``lock`` use full-tree :mod:`auctelis.inventory` adapters.
This module owns the read-only host surface walk and throwaway staging so durable
artifact trees never receive raw host config.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

# Relative to the user home directory. Keep this local-only and read-only.
# `~/.claude.json` is Claude Code's primary user/local MCP registry (docs).
HOST_RELATIVE_SURFACES: tuple[tuple[str, str], ...] = (
    ("cursor", ".cursor"),
    ("claude-code", ".claude"),
    ("claude-code", ".claude.json"),
    ("claude-code", ".mcp.json"),
    ("claude-desktop", "AppData/Roaming/Claude"),
    ("claude-desktop", "Library/Application Support/Claude"),
    ("vscode", ".vscode"),
    ("codex", ".codex"),
    ("codex", ".codex/config.toml"),
    ("windsurf", ".codeium/windsurf"),
    ("gemini", ".gemini"),
    ("zed", ".config/zed"),
)

# Relative to a project / cwd. Used by archived watch/allow staging only.
# Repo `check` / `lock` use full-tree DISCOVERY_ADAPTERS (skills, rules, …).
PROJECT_RELATIVE_SURFACES: tuple[tuple[str, str], ...] = (
    ("project-mcp", ".mcp.json"),
    ("project-cursor", ".cursor/mcp.json"),
    ("project-cursor", ".cursor/hooks.json"),
    ("project-cursor", ".cursor/rules"),
    ("project-claude", ".claude/settings.json"),
    ("project-claude", ".claude/settings.local.json"),
    ("project-claude", ".claude/commands"),
    ("project-claude", ".claude/hooks"),
    ("project-claude", ".claude/skills"),
    ("project-claude", ".claude/agents"),
    ("project-skills", "skills"),
    ("project-instructions", "AGENTS.md"),
    ("project-instructions", "CLAUDE.md"),
    ("project-instructions", "GEMINI.md"),
    ("project-instructions", "CODEX.md"),
    ("project-instructions", ".cursorrules"),
    ("project-instructions", ".windsurfrules"),
    ("project-instructions", ".clinerules"),
    ("project-instructions", ".github/copilot-instructions.md"),
    ("project-vscode", ".vscode/mcp.json"),
)


@dataclass(slots=True)
class HostSurface:
    host_id: str
    path: Path
    exists: bool


def stage_host_target(surface: HostSurface, stack: ExitStack) -> Path:
    """Stage a scan root that preserves adapter-relative paths.

    Claude Code's ``~/.claude/settings.json`` must appear as
    ``.claude/settings.json`` relative to the scan root, otherwise hooks and
    permission rules are invisible. Lone files (``.claude.json``) are copied
    as-is into a throwaway dir so RULE-012 can still see literal env values;
    durable ``-o`` trees never receive those copies.
    """
    path = surface.path
    if path.is_file():
        synth_tmp = stack.enter_context(
            tempfile.TemporaryDirectory(prefix=f"auctelis-doctor-{surface.host_id}-")
        )
        synth = Path(synth_tmp)
        # Scan needs real values for secret/pin rules; synth is throwaway.
        shutil.copy2(path, synth / path.name)
        return synth

    # Directory surfaces that are themselves a dotted host folder (e.g. ~/.claude)
    # must be nested so collectors see `.claude/...` relative paths.
    if path.name in {".claude", ".cursor", ".codex", ".gemini", ".vscode"}:
        synth_tmp = stack.enter_context(
            tempfile.TemporaryDirectory(prefix=f"auctelis-doctor-{surface.host_id}-")
        )
        synth = Path(synth_tmp)
        dest = synth / path.name
        shutil.copytree(path, dest, dirs_exist_ok=True)
        return synth

    return path


def discover_host_surfaces(*, home: Path | None = None) -> list[HostSurface]:
    root = (home or Path.home()).expanduser().resolve()
    found: list[HostSurface] = []
    seen: set[Path] = set()
    for host_id, rel in HOST_RELATIVE_SURFACES:
        path = (root / rel).resolve()
        if path in seen:
            continue
        seen.add(path)
        found.append(HostSurface(host_id=host_id, path=path, exists=path.exists()))
    return found


def discover_project_surfaces(*, root: Path | None = None) -> list[HostSurface]:
    """Discover authority files in a project tree (cwd / cloned repo)."""
    base = (root or Path.cwd()).expanduser().resolve()
    found: list[HostSurface] = []
    seen: set[Path] = set()
    for host_id, rel in PROJECT_RELATIVE_SURFACES:
        path = (base / rel).resolve()
        if path in seen:
            continue
        seen.add(path)
        found.append(HostSurface(host_id=host_id, path=path, exists=path.exists()))
    return found


def _merge_staged_into(synth: Path, staged: Path) -> None:
    if not staged.exists():
        return
    if staged.is_file():
        dest = synth / staged.name
        if not dest.exists():
            shutil.copy2(staged, dest)
        return
    for item in staged.iterdir():
        dest = synth / item.name
        if item.is_dir():
            if dest.exists():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copytree(item, dest)
        elif not dest.exists():
            shutil.copy2(item, dest)


def stage_all_host_surfaces(
    stack: ExitStack,
    *,
    home: Path | None = None,
) -> tuple[Path, list[HostSurface]]:
    """Merge every present host surface into one synth root (for ``lock --home``).

    Mirrors doctor staging so ``~/.cursor`` and ``~/.claude`` are both sealed,
    not only the first present path. Caller must keep ``stack`` alive while the
    returned path is used.
    """
    surfaces = discover_host_surfaces(home=home)
    present = [s for s in surfaces if s.exists]
    synth_tmp = stack.enter_context(tempfile.TemporaryDirectory(prefix="auctelis-home-lock-"))
    synth = Path(synth_tmp)
    for surface in present:
        staged = stage_host_target(surface, stack)
        _merge_staged_into(synth, staged)
    return synth, present


def stage_project_surfaces(
    stack: ExitStack,
    *,
    root: Path | None = None,
) -> tuple[Path, list[HostSurface]]:
    """Stage project-level authority files into a synth root."""
    surfaces = discover_project_surfaces(root=root)
    present = [s for s in surfaces if s.exists]
    synth_tmp = stack.enter_context(tempfile.TemporaryDirectory(prefix="auctelis-project-"))
    synth = Path(synth_tmp)
    for surface in present:
        path = surface.path
        rel = path.name
        # Preserve dotted project layout (.claude/, .cursor/, .mcp.json).
        try:
            project_root = (root or Path.cwd()).expanduser().resolve()
            rel_path = path.relative_to(project_root)
        except ValueError:
            rel_path = Path(rel)
        dest = synth / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            shutil.copy2(path, dest)
        elif path.is_dir():
            shutil.copytree(path, dest, dirs_exist_ok=True)
    return synth, present


def stage_watch_root(
    stack: ExitStack,
    *,
    home: Path | None = None,
    project: Path | None = None,
) -> tuple[Path, list[HostSurface]]:
    """Merge home host surfaces + optional project authority files for ``watch`` / seal."""
    home_synth, home_present = stage_all_host_surfaces(stack, home=home)
    synth_tmp = stack.enter_context(tempfile.TemporaryDirectory(prefix="auctelis-watch-"))
    synth = Path(synth_tmp)
    _merge_staged_into(synth, home_synth)
    project_present: list[HostSurface] = []
    if project is not None:
        project_synth, project_present = stage_project_surfaces(stack, root=project)
        _merge_staged_into(synth, project_synth)
    return synth, [*home_present, *project_present]
