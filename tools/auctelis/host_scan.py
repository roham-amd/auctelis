"""Host config discovery and staging for `watch` / `doctor` / `lock --home`.

This module owns the read-only host surface walk so the product front door
(`watch`) does not depend on the `doctor` CLI module. Staging preserves
adapter-relative paths (`.claude/settings.json`, `.cursor/mcp.json`) and copies
lone config files into a throwaway directory so durable artifact trees never
receive raw host config.
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
        for item in staged.iterdir():
            dest = synth / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copytree(item, dest)
            elif not dest.exists():
                shutil.copy2(item, dest)
    return synth, present
