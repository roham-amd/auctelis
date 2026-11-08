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

_SECRET_KEY_FRAGMENTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
    "access_key",
)


def _looks_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(frag in lowered for frag in _SECRET_KEY_FRAGMENTS)


def _redact_json_value(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: _redact_json_value(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_json_value(v) for v in value]
    if key is not None and _looks_secret_key(key) and value not in (None, ""):
        return "${REDACTED}"
    if isinstance(value, str) and key and key.lower() in {"env", "environment"}:
        return "${REDACTED}"
    return value


def _copy_host_config_redacted(src: Path, dest: Path) -> None:
    """Copy a host config for scanning without persisting secret-shaped literals."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        import json

        raw = src.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
        redacted = _redact_json_value(data)
        # Also scrub nested MCP env maps regardless of parent key naming.
        if isinstance(redacted, dict):
            for servers_key in ("mcpServers", "servers"):
                servers = redacted.get(servers_key)
                if isinstance(servers, dict):
                    for cfg in servers.values():
                        if isinstance(cfg, dict):
                            for env_key in ("env", "environment"):
                                env = cfg.get(env_key)
                                if isinstance(env, dict):
                                    cfg[env_key] = {str(k): "${REDACTED}" for k in env}
        dest.write_text(json.dumps(redacted, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError):
        # Non-JSON host files: copy bytes but never into a durable -o tree
        # (caller stages dest under TemporaryDirectory).
        shutil.copy2(src, dest)


@dataclass(slots=True)
class HostSurface:
    host_id: str
    path: Path
    exists: bool


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
            # Lone host files (e.g. ~/.claude.json) often hold MCP env secrets.
            # Always stage a redacted copy under a throwaway dir — never under -o.
            if surface.path.is_file():
                synth_tmp = stack.enter_context(
                    tempfile.TemporaryDirectory(prefix=f"authdiff-doctor-{surface.host_id}-")
                )
                synth = Path(synth_tmp)
                _copy_host_config_redacted(surface.path, synth / surface.path.name)
                target = synth
            else:
                target = surface.path
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
