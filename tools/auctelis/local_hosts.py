"""Read-only discovery and audit of installed local agent host configs."""

from __future__ import annotations

import shutil
import tempfile
import urllib.error
from pathlib import Path
from typing import Any

from auctelis.inspect_target import inspect_target
from auctelis.security.artifact_vet import run_artifact_vet

LOCAL_HOST_PATHS = (
    ("cursor", ".cursor/mcp.json"),
    ("claude-code", ".claude.json"),
    ("claude-code", ".claude/settings.json"),
    ("codex", ".codex/config.toml"),
    ("gemini", ".gemini/settings.json"),
    ("opencode", ".config/opencode/opencode.json"),
    ("continue", ".continue/config.json"),
)


def discover_local_host_configs(home: Path) -> list[tuple[str, str, Path]]:
    home_res = home.resolve()
    out: list[tuple[str, str, Path]] = []
    for host_id, rel in LOCAL_HOST_PATHS:
        p = home / rel
        if p.is_file() and p.resolve().is_relative_to(home_res):
            out.append((host_id, rel, p))
    return out


def inspect_local_hosts(*, home: Path | None = None, offline: bool = False) -> dict[str, Any]:
    root = Path.home() if home is None else Path(home)
    discovered = discover_local_host_configs(root)
    with tempfile.TemporaryDirectory(prefix="auctelis-local-hosts-") as tmp:
        tree = Path(tmp)
        for _host, rel, src in discovered:
            dest = tree / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        doc = inspect_target(str(tree), offline=True)

    doc["target"] = "local-hosts"
    doc["target_kind"] = "local_hosts"
    provenance = doc.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
        doc["provenance"] = provenance
    provenance["discovered_hosts"] = [{"host": h, "path": r} for h, r, _ in discovered]

    if not offline:
        reach = doc.get("reach") or {}
        red_flags = doc.setdefault("red_flags", [])
        unverified = doc.setdefault("unverified", [])
        for package in reach["unpinned_mcp"]:
            spec = str(package)
            try:
                report = run_artifact_vet(spec)
            except (OSError, ValueError, urllib.error.URLError) as exc:
                unverified.append(f"artifact vet fetch failed for {spec}: {exc}")
                continue
            for finding in report.findings:
                red_flags.append(
                    {
                        "rule_id": finding.code,
                        "severity": finding.severity,
                        "title": finding.summary,
                        "path": "",
                        "evidence": finding.evidence,
                    }
                )

    return doc
