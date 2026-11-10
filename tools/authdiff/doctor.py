"""Host-level authority map (`authdiff doctor`).

Reads the operator's own agent-host configuration directories (Cursor, Claude Code,
VS Code) and runs the same Guard scan engine. Designed for a non-empty first
experience: every developer machine usually has *something* configured.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from authdiff.security.gating import is_gate_finding
from authdiff.security.scan import run_scan

# Relative to the user home directory. Keep this local-only and read-only.
# `~/.claude.json` is Claude Code's primary user/local MCP registry (docs).
_HOST_RELATIVE_SURFACES: tuple[tuple[str, str], ...] = (
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

_SEV_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}


@dataclass(slots=True)
class HostSurface:
    host_id: str
    path: Path
    exists: bool


def _stage_host_target(surface: HostSurface, stack: ExitStack) -> Path:
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
            tempfile.TemporaryDirectory(prefix=f"authdiff-doctor-{surface.host_id}-")
        )
        synth = Path(synth_tmp)
        # Scan needs real values for secret/pin rules; synth is throwaway.
        shutil.copy2(path, synth / path.name)
        return synth

    # Directory surfaces that are themselves a dotted host folder (e.g. ~/.claude)
    # must be nested so collectors see `.claude/...` relative paths.
    if path.name in {".claude", ".cursor", ".codex", ".gemini", ".vscode"}:
        synth_tmp = stack.enter_context(
            tempfile.TemporaryDirectory(prefix=f"authdiff-doctor-{surface.host_id}-")
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
    for host_id, rel in _HOST_RELATIVE_SURFACES:
        path = (root / rel).resolve()
        if path in seen:
            continue
        seen.add(path)
        found.append(HostSurface(host_id=host_id, path=path, exists=path.exists()))
    return found


def _render_doctor_summary(
    *,
    surfaces: list[HostSurface],
    scans: list[dict[str, Any]],
) -> str:
    lines = [
        "authdiff doctor — host authority map",
        "Local-only read of your agent host configs. Nothing is uploaded.",
        "",
        "Surfaces:",
    ]
    for surface in surfaces:
        mark = "present" if surface.exists else "absent"
        lines.append(f"  - {surface.host_id}: {surface.path} ({mark})")
    lines.append("")

    total_gated = 0
    total_caps = 0
    top_risks: list[tuple[str, Any]] = []
    for item in scans:
        scan = item["scan"]
        gated = [f for f in scan.findings if is_gate_finding(f)]
        caps = [f for f in scan.findings if f.finding_class == "CAPABILITY"]
        total_gated += len(gated)
        total_caps += len(caps)
        for finding in gated:
            top_risks.append((item["host_id"], finding))
        lines.append(f"## {item['host_id']} @ {item['path']}")
        lines.append(
            f"components={len(scan.inventory.get('components') or [])} "
            f"gated={len(gated)} capabilities={len(caps)}"
        )
        show = gated or scan.findings[:5]
        for finding in show[:8]:
            fix = f" | fix: {finding.fix_snippet}" if finding.fix_snippet else ""
            lines.append(
                f"  [{finding.severity}/{finding.finding_class}] "
                f"{finding.rule_id} {finding.title}{fix}"
            )
        if not show:
            lines.append("  (no deterministic findings on this surface)")
        lines.append("")

    top_risks.sort(key=lambda pair: _SEV_RANK.get(pair[1].severity, 9))
    lines.append("## Top risks on this machine")
    if not top_risks:
        lines.append("  (no gated findings — still NOT a clearance; effective perms unverified)")
    else:
        for host_id, finding in top_risks[:3]:
            lines.append(f"  [{finding.severity}] {host_id}: {finding.rule_id} {finding.title}")
    lines.append("")
    lines.append(f"Totals: gated_findings={total_gated} capability_observations={total_caps}")
    lines.append(
        "Coverage honesty: host effective permissions remain NOT VERIFIED; "
        "absence of findings is not a clearance."
    )
    if top_risks:
        lines.append(
            "Next: `authdiff harden --findings <doctor-out>/<surface>/findings.json` "
            "for dry-run fix patches."
        )
    return "\n".join(lines)


def run_doctor(
    *,
    home: Path | None = None,
    output_dir: Path | None = None,
    fail_on: str | None = None,
) -> tuple[str, int]:
    """Scan discovered host configs; return (summary_text, exit_code)."""
    surfaces = discover_host_surfaces(home=home)
    present = [s for s in surfaces if s.exists]
    if not present:
        text = (
            "authdiff doctor — no host config surfaces found under "
            f"{(home or Path.home()).expanduser()}.\n"
            "Looked for: "
            + ", ".join(f"~/{rel}" for _, rel in _HOST_RELATIVE_SURFACES)
            + "\nInstall Cursor/Claude Code configs, or run `authdiff scan <path>` on a repo."
        )
        return text, 0

    with ExitStack() as stack:
        if output_dir is None:
            tmp = stack.enter_context(tempfile.TemporaryDirectory(prefix="authdiff-doctor-"))
            out_root = Path(tmp)
        else:
            out_root = output_dir
            out_root.mkdir(parents=True, exist_ok=True)

        scans: list[dict[str, Any]] = []
        worst_code = 0
        for surface in present:
            target = _stage_host_target(surface, stack)
            dest = out_root / f"{surface.host_id}-{surface.path.name}".replace(".", "_")
            scan, _payload, code = run_scan(
                target,
                output_dir=dest,
                fail_on=fail_on,
                policy=None,
            )
            worst_code = max(worst_code, code)
            scans.append({"host_id": surface.host_id, "path": str(surface.path), "scan": scan})

        return _render_doctor_summary(surfaces=surfaces, scans=scans), worst_code
