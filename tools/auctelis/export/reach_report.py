"""Shareable Agent Reach Report — HTML / Markdown / JSON + honesty panel.

This is an audit artifact, not a safety certificate. It reuses the check report
and the authority SBOM builder so pilots can forward what ``auctelis check``
already computes.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, cast

from auctelis.export.authority_sbom import build_authority_sbom
from auctelis.inventory.coverage import (
    family_coverage_line_from_coverage,
    truncation_honesty_notes,
)
from auctelis.jsonio import write_json, write_text
from auctelis.security.engine import ScanResult
from auctelis.versioning import product_version

REPORT_SCHEMA = "auctelis.reach_report.v1"


def _as_dict(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    return cast(list[Any], value) if isinstance(value, list) else []


def build_reach_report(
    report: dict[str, Any],
    scan: ScanResult | None,
    *,
    cards: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble a versioned reach-report document from a check report + scan."""
    coverage = _as_dict(report.get("coverage"))
    if not coverage and scan is not None and isinstance(scan.coverage, dict):
        coverage = scan.coverage
    unparsed = int(report.get("unparsed") or 0)
    coverage_line = str(report.get("coverage_line") or "").strip()
    if not coverage_line:
        coverage_line = family_coverage_line_from_coverage(coverage, unparsed=unparsed)
    honesty = {
        "disclaimer": (
            "This report describes DECLARED/CONFIGURED agent authority observed by a "
            "passive scan. It is not a safety certificate, does not prove EFFECTIVE "
            "permissions, and does not establish VERIFIED runtime behavior."
        ),
        "coverage_line": coverage_line,
        "truncation": truncation_honesty_notes(coverage),
        "unparsed": unparsed,
        "declared_only": True,
    }
    reach = _as_dict(report.get("reach"))
    return {
        "schema": REPORT_SCHEMA,
        "product": "auctelis",
        "product_version": product_version(),
        "repository": report.get("repository"),
        "audited_commit": (
            getattr(scan, "commit", None) if scan is not None else report.get("audited_commit")
        ),
        "honesty": honesty,
        "coverage": coverage,
        "reach": reach,
        "pins": _as_dict(report.get("pins")),
        "counts": _as_dict(report.get("counts")),
        "delta": _as_dict(report.get("delta")),
        "label": report.get("label"),
        "verdict": report.get("verdict"),
        "cards": list(cards or _as_list(reach.get("top_cards"))),
        "check": {
            "schema_version": report.get("schema_version"),
            "lock_path": report.get("lock_path"),
            "lock_present": report.get("lock_present"),
            "first_run": report.get("first_run"),
            "meaningful": report.get("meaningful"),
        },
    }


def diff_reach_reports(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """Compare two reach-report documents (or check JSON with a ``reach`` block)."""

    def _identity(item: dict[str, Any]) -> str:
        kind = str(item.get("kind") or "")
        name = str(item.get("name") or "")
        path = str(item.get("path") or "")
        return f"{kind}|{name}|{path}"

    def _top_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
        reach = _as_dict(doc.get("reach"))
        out: dict[str, dict[str, Any]] = {}
        for item in _as_list(reach.get("top")):
            if isinstance(item, dict):
                out[_identity(item)] = item
        return out

    before_map = _top_map(before)
    after_map = _top_map(after)
    before_keys = set(before_map)
    after_keys = set(after_map)
    added = [after_map[k] for k in sorted(after_keys - before_keys)]
    removed = [before_map[k] for k in sorted(before_keys - after_keys)]
    changed: list[dict[str, Any]] = []
    for key in sorted(before_keys & after_keys):
        b, a = before_map[key], after_map[key]
        if b.get("tier") != a.get("tier") or b.get("reason") != a.get("reason"):
            changed.append({"before": b, "after": a})

    def _tier_counts(doc: dict[str, Any]) -> dict[str, int]:
        reach = _as_dict(doc.get("reach"))
        raw = _as_dict(reach.get("tier_counts"))
        return {
            "tier0": int(raw.get("tier0") or 0),
            "tier1": int(raw.get("tier1") or 0),
            "tier2": int(raw.get("tier2") or 0),
        }

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "tier_counts_before": _tier_counts(before),
        "tier_counts_after": _tier_counts(after),
        "changed_count": len(added) + len(removed) + len(changed),
    }


def render_reach_md(
    doc: dict[str, Any],
    *,
    baseline_diff: dict[str, Any] | None = None,
) -> str:
    """Render a Markdown reach report suitable for tickets / PRs."""
    honesty = _as_dict(doc.get("honesty"))
    reach = _as_dict(doc.get("reach"))
    tiers = _as_dict(reach.get("tier_counts"))
    lines: list[str] = [
        "# Auctelis Agent Reach Report",
        "",
        f"> {honesty.get('disclaimer') or 'Declared/configured authority only — not a certificate.'}",
        "",
        f"- **Product:** auctelis {doc.get('product_version') or product_version()}",
        f"- **Repository:** `{doc.get('repository') or ''}`",
        f"- **Reach total:** {reach.get('total', 0)}",
        (
            f"- **Tiers:** tier0={tiers.get('tier0', 0)} · "
            f"tier1={tiers.get('tier1', 0)} · tier2={tiers.get('tier2', 0)}"
        ),
        f"- **Coverage:** {honesty.get('coverage_line') or '(unavailable)'}",
        "",
        "## Honesty",
        "",
    ]
    trunc = _as_list(honesty.get("truncation"))
    if trunc:
        for note in trunc:
            lines.append(f"- {note}")
    else:
        lines.append("- No walk truncation reported for this scan.")
    lines.append("- Inventory is DECLARED/CONFIGURED only.")
    lines.extend(["", "## Tier-2 reach", ""])
    top = _as_list(reach.get("top"))
    tier2 = [item for item in top if isinstance(item, dict) and int(item.get("tier") or 0) >= 2]
    if not tier2:
        lines.append("_No tier-2 records in the top ranking._")
    else:
        for item in tier2:
            name = str(item.get("name") or "")
            path = str(item.get("path") or "")
            reason = str(item.get("reason") or item.get("card") or "")
            lines.append(f"- **{name}** (`{path}`) — {reason}")
    cards = _as_list(doc.get("cards"))
    if cards:
        lines.extend(["", "## Cards", ""])
        for card in cards:
            lines.append(f"- {card}")
    pins = _as_dict(doc.get("pins"))
    unpinned = _as_list(pins.get("items"))
    if unpinned:
        lines.extend(["", "## Unpinned MCP launchers", ""])
        for item in unpinned:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{item.get('name')}` ({item.get('path')}) — "
                f"{item.get('suggestion') or item.get('pin_state')}"
            )
    if baseline_diff:
        lines.extend(["", "## Baseline diff", ""])
        lines.append(f"- Added: {len(_as_list(baseline_diff.get('added')))}")
        lines.append(f"- Removed: {len(_as_list(baseline_diff.get('removed')))}")
        lines.append(f"- Changed: {len(_as_list(baseline_diff.get('changed')))}")
        for item in _as_list(baseline_diff.get("added")):
            if isinstance(item, dict):
                lines.append(f"  - + {item.get('kind')} `{item.get('name')}` ({item.get('path')})")
        for item in _as_list(baseline_diff.get("removed")):
            if isinstance(item, dict):
                lines.append(f"  - - {item.get('kind')} `{item.get('name')}` ({item.get('path')})")
    lines.append("")
    return "\n".join(lines)


def render_reach_html(
    doc: dict[str, Any],
    *,
    baseline_diff: dict[str, Any] | None = None,
) -> str:
    """Render a self-contained HTML report (stdlib escaping only)."""
    honesty = _as_dict(doc.get("honesty"))
    reach = _as_dict(doc.get("reach"))
    tiers = _as_dict(reach.get("tier_counts"))
    esc = html.escape

    def _li(text: str) -> str:
        return f"<li>{esc(text)}</li>"

    trunc_html = "".join(_li(str(n)) for n in _as_list(honesty.get("truncation")))
    if not trunc_html:
        trunc_html = "<li>No walk truncation reported for this scan.</li>"

    tier2_rows: list[str] = []
    for item in _as_list(reach.get("top")):
        if not isinstance(item, dict) or int(item.get("tier") or 0) < 2:
            continue
        tier2_rows.append(
            "<tr>"
            f"<td>{esc(str(item.get('name') or ''))}</td>"
            f"<td><code>{esc(str(item.get('path') or ''))}</code></td>"
            f"<td>{esc(str(item.get('reason') or ''))}</td>"
            "</tr>"
        )
    if not tier2_rows:
        tier2_body = "<tr><td colspan='3'><em>No tier-2 records in the top ranking.</em></td></tr>"
    else:
        tier2_body = "".join(tier2_rows)

    cards_html = "".join(_li(str(c)) for c in _as_list(doc.get("cards")))
    baseline_section = ""
    if baseline_diff:
        parts = [
            f"<p>Added {len(_as_list(baseline_diff.get('added')))}, "
            f"removed {len(_as_list(baseline_diff.get('removed')))}, "
            f"changed {len(_as_list(baseline_diff.get('changed')))}.</p>",
            "<ul>",
        ]
        for item in _as_list(baseline_diff.get("added")):
            if isinstance(item, dict):
                parts.append(_li(f"+ {item.get('kind')} {item.get('name')} ({item.get('path')})"))
        for item in _as_list(baseline_diff.get("removed")):
            if isinstance(item, dict):
                parts.append(_li(f"- {item.get('kind')} {item.get('name')} ({item.get('path')})"))
        parts.append("</ul>")
        baseline_section = "<section><h2>Baseline diff</h2>" + "".join(parts) + "</section>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Auctelis Agent Reach Report</title>
<style>
body {{ font-family: Georgia, "Times New Roman", serif; margin: 2rem; max-width: 52rem;
  background: linear-gradient(180deg, #f7f4ef 0%, #ebe6dc 100%); color: #1c1917; }}
h1 {{ font-size: 1.75rem; letter-spacing: -0.02em; }}
.banner {{ border-left: 4px solid #b45309; padding: 0.75rem 1rem; background: #fff7ed; margin: 1rem 0; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border-bottom: 1px solid #d6d3d1; padding: 0.4rem 0.5rem; text-align: left; vertical-align: top; }}
code {{ font-family: ui-monospace, Consolas, monospace; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Auctelis Agent Reach Report</h1>
<p class="banner">{esc(str(honesty.get("disclaimer") or ""))}</p>
<ul>
<li><strong>Product:</strong> auctelis {esc(str(doc.get("product_version") or product_version()))}</li>
<li><strong>Repository:</strong> <code>{esc(str(doc.get("repository") or ""))}</code></li>
<li><strong>Reach total:</strong> {esc(str(reach.get("total", 0)))}</li>
<li><strong>Tiers:</strong> tier0={esc(str(tiers.get("tier0", 0)))} ·
 tier1={esc(str(tiers.get("tier1", 0)))} · tier2={esc(str(tiers.get("tier2", 0)))}</li>
<li><strong>Coverage:</strong> {esc(str(honesty.get("coverage_line") or "(unavailable)"))}</li>
</ul>
<section>
<h2>Honesty</h2>
<ul>{trunc_html}<li>Inventory is DECLARED/CONFIGURED only.</li></ul>
</section>
<section>
<h2>Tier-2 reach</h2>
<table>
<thead><tr><th>Name</th><th>Path</th><th>Reason</th></tr></thead>
<tbody>{tier2_body}</tbody>
</table>
</section>
<section>
<h2>Cards</h2>
<ul>{cards_html or "<li><em>None</em></li>"}</ul>
</section>
{baseline_section}
</body>
</html>
"""


def write_reach_report_artifacts(
    out_dir: Path,
    report: dict[str, Any],
    scan: ScanResult | None,
    *,
    cards: list[str] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``reach-report.{html,md,json}`` and ``authority-sbom.json`` under ``out_dir``."""
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = build_reach_report(report, scan, cards=cards)
    baseline_diff = diff_reach_reports(baseline, doc) if baseline else None
    if baseline_diff is not None:
        doc["baseline_diff"] = baseline_diff
    write_json(out_dir / "reach-report.json", doc)
    write_text(out_dir / "reach-report.md", render_reach_md(doc, baseline_diff=baseline_diff))
    write_text(out_dir / "reach-report.html", render_reach_html(doc, baseline_diff=baseline_diff))
    if scan is not None:
        write_json(out_dir / "authority-sbom.json", build_authority_sbom(scan))
    return doc


def load_reach_baseline(path: Path) -> dict[str, Any]:
    """Load a prior reach-report.json (or check --json) for ``--baseline``."""
    data = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"--baseline must be a JSON object: {path}")
    return data
