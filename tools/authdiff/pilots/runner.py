"""Run Guard scans against the curated pilot repository manifest."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from authdiff.jsonio import write_json, write_text
from authdiff.paths import repo_root
from authdiff.security.scan import run_scan
from authdiff.versioning import package_version, product_version


def default_manifest_path() -> Path:
    return repo_root() / "docs" / "archive" / "pilots" / "manifest.json"


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or default_manifest_path()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("pilots"), list):
        raise ValueError(f"Invalid pilot manifest: {manifest_path}")
    return data


def run_pilots(
    *,
    manifest_path: Path | None = None,
    output_dir: Path | None = None,
    only: list[str] | None = None,
) -> dict[str, Any]:
    """Scan each enabled pilot target; write per-pilot artifacts + summary."""
    manifest = load_manifest(manifest_path)
    root = repo_root()
    out_root = (output_dir or (root / "docs" / "archive" / "pilots" / "results")).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    wanted = set(only) if only else None
    results: list[dict[str, Any]] = []

    for entry in manifest["pilots"]:
        pilot_id = str(entry.get("id") or "")
        if not pilot_id:
            continue
        if wanted is not None and pilot_id not in wanted:
            continue
        if entry.get("enabled") is False:
            results.append(
                {
                    "id": pilot_id,
                    "status": "skipped",
                    "reason": "disabled in manifest",
                }
            )
            continue
        rel = entry.get("path")
        if not rel:
            results.append({"id": pilot_id, "status": "error", "reason": "missing path"})
            continue
        target = (root / str(rel)).resolve() if not entry.get("absolute") else Path(str(rel))
        if not target.is_dir():
            results.append(
                {
                    "id": pilot_id,
                    "status": "missing",
                    "path": str(target),
                    "reason": "target directory not found",
                }
            )
            continue
        pilot_out = out_root / pilot_id
        scan, payload, _code = run_scan(target, output_dir=pilot_out, fail_on=None)
        summary = {
            "id": pilot_id,
            "status": "ok",
            "path": str(target),
            "kind": entry.get("kind"),
            "notes": entry.get("notes"),
            "component_count": payload.get("component_count"),
            "finding_count": payload.get("finding_count"),
            "by_class": scan.findings_by_class(),
            "by_severity": scan.findings_by_severity(),
            "authority_bearing": scan.authority_bearing_count,
            "output_dir": str(pilot_out),
        }
        results.append(summary)

    summary_md = out_root / "summary.md"
    report = {
        "generated_at_utc": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "product_version": product_version(),
        "package_version": package_version(),
        "manifest": str((manifest_path or default_manifest_path()).resolve()),
        "pilot_count": len(results),
        "ok_count": sum(1 for r in results if r.get("status") == "ok"),
        "results": results,
        "summary_md": str(summary_md),
        "output_dir": str(out_root),
    }
    write_json(out_root / "summary.json", report)
    lines = [
        "# authdiff pilot scan summary",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Product: {report['product_version']} / tooling {report['package_version']}",
        f"- Pilots: {report['pilot_count']} (ok={report['ok_count']})",
        "",
        "| Pilot | Status | Components | Findings | Notes |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in results:
        lines.append(
            f"| `{row.get('id')}` | {row.get('status')} | "
            f"{row.get('component_count', '—')} | {row.get('finding_count', '—')} | "
            f"{row.get('notes') or row.get('reason') or ''} |"
        )
    lines.extend(
        [
            "",
            "These pilots validate install→scan usefulness on known fixtures and curated",
            "targets. They are **not** AgentSecBench external evidence and do not change N.",
            "",
        ]
    )
    write_text(summary_md, "\n".join(lines))
    return report
