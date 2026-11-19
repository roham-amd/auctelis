"""Shareable Agent Reach Report — HTML / Markdown / JSON + honesty panel.

This is an audit artifact, not a safety certificate. It reuses the check report
and the authority SBOM builder so pilots can forward what ``auctelis check``
already computes.
"""

from __future__ import annotations

import html
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from auctelis.export.authority_sbom import build_authority_sbom
from auctelis.inventory.coverage import (
    ADAPTER_COVERAGE,
    family_coverage_line_from_coverage,
    truncation_honesty_notes,
)
from auctelis.jsonio import write_json, write_text
from auctelis.security.engine import ScanResult
from auctelis.textutil import escape_markdown_inline, sanitize_terminal_line, strip_control
from auctelis.versioning import product_version

REPORT_SCHEMA = "auctelis.reach_report.v1"
FLEET_REPORT_SCHEMA = "auctelis.fleet_reach_report.v1"

FleetEntry = tuple[dict[str, Any], ScanResult | None, list[str] | None]

_DECLARED_ONLY_DISCLAIMER = (
    "This report describes DECLARED/CONFIGURED agent authority observed by a "
    "passive scan. It is not a safety certificate, does not prove EFFECTIVE "
    "permissions, and does not establish VERIFIED runtime behavior."
)

_NEXT_STEP_MD = (
    "_Next step: `auctelis init --lockless` to watch future agent-authority "
    "changes in one quiet PR comment._"
)
_NEXT_STEP_MD_PLURAL = (
    "_Next step: `auctelis init --lockless` in each repository to watch future "
    "agent-authority changes in one quiet PR comment._"
)


def _as_dict(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    return cast(list[Any], value) if isinstance(value, list) else []


def _manual_family_rows(doc: dict[str, Any]) -> list[tuple[str, str]]:
    """``(family, maturity)`` for families no passive adapter inspects."""
    coverage = _as_dict(doc.get("coverage"))
    families = [str(f) for f in _as_list(coverage.get("manual_review_families")) if str(f)]
    if not families:
        return []
    maturity = {
        str(row.get("family") or ""): str(row.get("maturity") or "") for row in ADAPTER_COVERAGE
    }
    return [(family, maturity.get(family, "")) for family in families]


def _manual_md_lines(doc: dict[str, Any]) -> list[str]:
    coverage = _as_dict(doc.get("coverage"))
    rows = _manual_family_rows(doc)
    lines = ["## Not auto-inspected", ""]
    if not coverage:
        lines.append("_Coverage metadata unavailable for this report._")
    elif not rows:
        lines.append("_No manual-review families reported._")
    else:
        for family, level in rows:
            lines.append(f"- {family}" + (f" ({level})" if level else ""))
        lines.extend(
            [
                "",
                "These families have no passive discovery adapter; they require manual review.",
            ]
        )
    lines.append("")
    return lines


def _next_step_html(*, plural: bool) -> str:
    where = "each repository" if plural else "this repository"
    return (
        "<footer><p><strong>Next step:</strong> "
        f"<code>auctelis init --lockless</code> in {where} to watch future "
        "agent-authority changes in one quiet PR comment.</p></footer>"
    )


def _manual_section_html(doc: dict[str, Any]) -> str:
    esc = html.escape
    rows = _manual_family_rows(doc)
    if not _as_dict(doc.get("coverage")):
        return (
            "<section><h2>Not auto-inspected</h2>"
            "<p><em>Coverage metadata unavailable for this report.</em></p></section>"
        )
    if rows:
        items = "".join(
            "<li><strong>"
            + esc(family)
            + "</strong>"
            + (f" · {esc(level)}" if level else "")
            + "</li>"
            for family, level in rows
        )
    else:
        items = "<li><em>No manual-review families reported.</em></li>"
    return (
        "<section><h2>Not auto-inspected</h2><ul>"
        + items
        + "</ul><p>These families have no passive discovery adapter; "
        "they require manual review.</p></section>"
    )


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
        "disclaimer": _DECLARED_ONLY_DISCLAIMER,
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

    def _record_list(doc: dict[str, Any]) -> list[Any]:
        """Prefer full ``records``; fall back to capped ``top`` for legacy JSON."""
        reach = _as_dict(doc.get("reach"))
        records = _as_list(reach.get("records"))
        if records:
            return records
        return _as_list(reach.get("top"))

    def _top_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for item in _record_list(doc):
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
    lines.append("")
    lines.extend(_manual_md_lines(doc))
    lines.extend(["## Tier-2 reach", ""])
    ranked = _as_list(reach.get("records")) or _as_list(reach.get("top"))
    tier2 = [item for item in ranked if isinstance(item, dict) and int(item.get("tier") or 0) >= 2]
    if not tier2:
        lines.append("_No tier-2 records in this inventory._")
    else:
        for item in tier2:
            name = escape_markdown_inline(str(item.get("name") or ""), max_len=160)
            path = _md_code(item.get("path"))
            reason = escape_markdown_inline(
                str(item.get("reason") or item.get("card") or ""), max_len=200
            )
            lines.append(f"- **{name}** ({path}) — {reason}")
    cards = _as_list(doc.get("cards"))
    if cards:
        lines.extend(["", "## Cards", ""])
        for card in cards:
            lines.append(f"- {strip_control(card)}")
        total = int(reach.get("total") or 0)
        shown = len(cards)
        if total > shown:
            lines.append(f"- _+{total - shown} more (see Tier-2 / full JSON)._")
    pins = _as_dict(doc.get("pins"))
    unpinned = _as_list(pins.get("items"))
    if unpinned:
        lines.extend(["", "## Unpinned MCP launchers", ""])
        for item in unpinned:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {_md_code(item.get('name'))} ({_md_code(item.get('path'))}) — "
                + escape_markdown_inline(
                    str(item.get("suggestion") or item.get("pin_state") or ""), max_len=200
                )
            )
    if baseline_diff:
        lines.extend(["", "## Baseline diff", ""])
        lines.append(f"- Added: {len(_as_list(baseline_diff.get('added')))}")
        lines.append(f"- Removed: {len(_as_list(baseline_diff.get('removed')))}")
        lines.append(f"- Changed: {len(_as_list(baseline_diff.get('changed')))}")
        for item in _as_list(baseline_diff.get("added")):
            if isinstance(item, dict):
                lines.append(
                    f"  - + {_md_code(item.get('kind'))} {_md_code(item.get('name'))} "
                    f"({_md_code(item.get('path'))})"
                )
        for item in _as_list(baseline_diff.get("removed")):
            if isinstance(item, dict):
                lines.append(
                    f"  - - {_md_code(item.get('kind'))} {_md_code(item.get('name'))} "
                    f"({_md_code(item.get('path'))})"
                )
    lines.extend(["", _NEXT_STEP_MD])
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

    ranked = _as_list(reach.get("records")) or _as_list(reach.get("top"))
    tier2_rows: list[str] = []
    for item in ranked:
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
        tier2_body = "<tr><td colspan='3'><em>No tier-2 records in this inventory.</em></td></tr>"
    else:
        tier2_body = "".join(tier2_rows)

    manual_section = _manual_section_html(doc)

    pins_doc = _as_dict(doc.get("pins"))
    unpinned_items = [item for item in _as_list(pins_doc.get("items")) if isinstance(item, dict)]
    if unpinned_items:
        pin_rows = "".join(
            "<tr>"
            f"<td>{esc(str(item.get('name') or ''))}</td>"
            f"<td><code>{esc(str(item.get('path') or ''))}</code></td>"
            f"<td>{esc(str(item.get('suggestion') or item.get('pin_state') or ''))}</td>"
            "</tr>"
            for item in unpinned_items
        )
        pins_section = (
            "<section><h2>Unpinned MCP launchers</h2>"
            "<table><thead><tr><th>Name</th><th>Path</th><th>Pin suggestion</th>"
            f"</tr></thead><tbody>{pin_rows}</tbody></table></section>"
        )
    else:
        pins_section = ""

    cards = _as_list(doc.get("cards"))
    cards_html = "".join(_li(str(c)) for c in cards)
    total = int(reach.get("total") or 0)
    if total > len(cards) > 0:
        cards_html += _li(f"+{total - len(cards)} more (see Tier-2 / full JSON).")
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
{manual_section}
<section>
<h2>Cards</h2>
<ul>{cards_html or "<li><em>None</em></li>"}</ul>
</section>
{pins_section}
{baseline_section}
{_next_step_html(plural=False)}
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
    """Load a prior reach-report.json (or check --json) for ``--baseline``.

    Raises ``ValueError`` (not ``SystemExit``) so callers decide the exit code.
    """
    resolved = path.expanduser().resolve()
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read --baseline {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"--baseline must be a JSON object: {path}")
    return data


# --- Fleet reach report (multi-repo audit sweep) ---------------------------


def build_fleet_reach_report(entries: Sequence[FleetEntry]) -> dict[str, Any]:
    """Assemble one ranked fleet document from several single-repo reports.

    ``entries`` is ``(check_report, scan, cards)`` per repository, exactly the
    shape ``build_check_report`` returns. Repositories are ranked by tier-2
    reach so the most dangerous repo appears first.
    """
    repositories: list[dict[str, Any]] = []
    manual: list[str] = []
    totals = {"reach_total": 0, "tier0": 0, "tier1": 0, "tier2": 0, "unpinned": 0}
    for report, scan, cards in entries:
        doc = build_reach_report(report, scan, cards=cards)
        repositories.append(doc)
        reach = _as_dict(doc.get("reach"))
        tiers = _as_dict(reach.get("tier_counts"))
        totals["reach_total"] += int(reach.get("total") or 0)
        for tier_key in ("tier0", "tier1", "tier2"):
            totals[tier_key] += int(tiers.get(tier_key) or 0)
        totals["unpinned"] += int(_as_dict(doc.get("pins")).get("unpinned") or 0)
        for family in _as_list(_as_dict(doc.get("coverage")).get("manual_review_families")):
            name = str(family)
            if name and name not in manual:
                manual.append(name)

    def _tier2(repo: dict[str, Any]) -> int:
        tiers = _as_dict(_as_dict(repo.get("reach")).get("tier_counts"))
        return int(tiers.get("tier2") or 0)

    repositories.sort(
        key=lambda repo: (
            -_tier2(repo),
            -int(_as_dict(repo.get("reach")).get("total") or 0),
            str(repo.get("repository") or ""),
        )
    )
    return {
        "schema": FLEET_REPORT_SCHEMA,
        "product": "auctelis",
        "product_version": product_version(),
        "honesty": {
            "disclaimer": _DECLARED_ONLY_DISCLAIMER,
            "declared_only": True,
            "manual_review_families": manual,
        },
        # Fleet-level coverage block so shared renderers can list blind spots.
        "coverage": {"manual_review_families": manual} if manual else {},
        "repository_count": len(repositories),
        "totals": totals,
        "repositories": repositories,
    }


def _md_code(value: object) -> str:
    """Backtick one value for Markdown without letting a backtick break the span."""
    return "`" + strip_control(str(value or "")).replace("`", "'") + "`"


def _fleet_repo_table_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [repo for repo in _as_list(doc.get("repositories")) if isinstance(repo, dict)]


def _fleet_pin_items(repo: dict[str, Any]) -> list[dict[str, Any]]:
    pins = _as_dict(repo.get("pins"))
    return [item for item in _as_list(pins.get("items")) if isinstance(item, dict)]


def _tier2_records(repo: dict[str, Any]) -> list[dict[str, Any]]:
    reach = _as_dict(repo.get("reach"))
    ranked = _as_list(reach.get("records")) or _as_list(reach.get("top"))
    return [item for item in ranked if isinstance(item, dict) and int(item.get("tier") or 0) >= 2]


def render_fleet_summary(doc: dict[str, Any]) -> str:
    """Compact terminal summary for a multi-repo ``check --report`` run."""
    totals = _as_dict(doc.get("totals"))
    lines = [
        (
            f"auctelis check · fleet reach report · "
            f"{int(doc.get('repository_count') or 0)} repositories"
        ),
        (
            f"Reach: {int(totals.get('reach_total') or 0)} records · tier 2 fail "
            f"{int(totals.get('tier2') or 0)} · tier 1 comment "
            f"{int(totals.get('tier1') or 0)} · tier 0 silent "
            f"{int(totals.get('tier0') or 0)}"
        ),
        (
            f"Pins: {int(totals.get('unpinned') or 0)} unpinned MCP "
            f"{'launcher' if int(totals.get('unpinned') or 0) == 1 else 'launchers'}"
        ),
        "",
    ]
    for repo in _fleet_repo_table_rows(doc):
        reach = _as_dict(repo.get("reach"))
        tiers = _as_dict(reach.get("tier_counts"))
        total = int(reach.get("total") or 0)
        noun = "record" if total == 1 else "records"
        lines.append(
            f"  {repo.get('repository') or '?'} · tier 2 {int(tiers.get('tier2') or 0)}"
            f" · {total} {noun}"
        )
    return "\n".join(sanitize_terminal_line(line) for line in lines)


def render_fleet_reach_md(doc: dict[str, Any]) -> str:
    """Render the fleet reach report as Markdown (shareable in tickets)."""
    totals = _as_dict(doc.get("totals"))
    repositories = _fleet_repo_table_rows(doc)
    lines: list[str] = [
        "# Auctelis Fleet Agent Reach Report",
        "",
        f"> {_DECLARED_ONLY_DISCLAIMER}",
        "",
        f"- **Product:** auctelis {doc.get('product_version') or product_version()}",
        f"- **Repositories:** {int(doc.get('repository_count') or 0)}",
        f"- **Reach total:** {int(totals.get('reach_total') or 0)}",
        (
            f"- **Tiers:** tier0={int(totals.get('tier0') or 0)} · "
            f"tier1={int(totals.get('tier1') or 0)} · "
            f"tier2={int(totals.get('tier2') or 0)}"
        ),
        f"- **Unpinned MCP launchers:** {int(totals.get('unpinned') or 0)}",
        "",
        "## Repositories (ranked by tier-2 reach)",
        "",
        "| Repository | Reach | tier2 | tier1 | tier0 | Unpinned |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for repo in repositories:
        reach = _as_dict(repo.get("reach"))
        tiers = _as_dict(reach.get("tier_counts"))
        lines.append(
            f"| {_md_code(repo.get('repository'))} | "
            f"{int(reach.get('total') or 0)} | {int(tiers.get('tier2') or 0)} | "
            f"{int(tiers.get('tier1') or 0)} | {int(tiers.get('tier0') or 0)} | "
            f"{int(_as_dict(repo.get('pins')).get('unpinned') or 0)} |"
        )
    lines.extend(["", "## Tier-2 reach by repository", ""])
    any_tier2 = False
    for repo in repositories:
        tier2 = _tier2_records(repo)
        lines.append(f"### {_md_code(repo.get('repository'))}")
        lines.append("")
        if not tier2:
            lines.append("_No tier-2 records._")
        else:
            any_tier2 = True
            for item in tier2:
                reason = escape_markdown_inline(
                    str(item.get("reason") or item.get("card") or ""), max_len=200
                )
                lines.append(
                    f"- **{escape_markdown_inline(str(item.get('name') or ''))}** "
                    f"({_md_code(item.get('path'))}) — {reason}"
                )
        lines.append("")
    if not any_tier2:
        lines.append("_No tier-2 records across these repositories._")
        lines.append("")
    lines.extend(["## Unpinned MCP launchers", ""])
    any_pins = False
    for repo in repositories:
        items = _fleet_pin_items(repo)
        if not items:
            continue
        any_pins = True
        lines.append(f"### {_md_code(repo.get('repository'))}")
        lines.append("")
        for item in items:
            suggestion = escape_markdown_inline(
                str(item.get("suggestion") or item.get("pin_state") or ""), max_len=200
            )
            lines.append(
                f"- {_md_code(item.get('name'))} ({_md_code(item.get('path'))}) — {suggestion}"
            )
        lines.append("")
    if not any_pins:
        lines.extend(["_No unpinned MCP launchers across these repositories._", ""])
    lines.extend(_manual_md_lines(doc))
    lines.extend([_NEXT_STEP_MD_PLURAL, ""])
    return "\n".join(lines)


def render_fleet_reach_html(doc: dict[str, Any]) -> str:
    """Render the fleet reach report as one self-contained HTML file."""
    esc = html.escape
    totals = _as_dict(doc.get("totals"))
    repositories = _fleet_repo_table_rows(doc)

    summary_rows = (
        "".join(
            "<tr>"
            f"<td><code>{esc(str(repo.get('repository') or ''))}</code></td>"
            f"<td>{int(_as_dict(repo.get('reach')).get('total') or 0)}</td>"
            f"<td>{int(_as_dict(_as_dict(repo.get('reach')).get('tier_counts')).get('tier2') or 0)}</td>"
            f"<td>{int(_as_dict(_as_dict(repo.get('reach')).get('tier_counts')).get('tier1') or 0)}</td>"
            f"<td>{int(_as_dict(_as_dict(repo.get('reach')).get('tier_counts')).get('tier0') or 0)}</td>"
            f"<td>{int(_as_dict(repo.get('pins')).get('unpinned') or 0)}</td>"
            "</tr>"
            for repo in repositories
        )
        or "<tr><td colspan='6'><em>No repositories.</em></td></tr>"
    )

    detail_parts: list[str] = []
    pin_parts: list[str] = []
    for repo in repositories:
        name = esc(str(repo.get("repository") or ""))
        tier2_rows = (
            "".join(
                "<tr>"
                f"<td>{esc(str(item.get('name') or ''))}</td>"
                f"<td><code>{esc(str(item.get('path') or ''))}</code></td>"
                f"<td>{esc(str(item.get('reason') or ''))}</td>"
                "</tr>"
                for item in _tier2_records(repo)
            )
            or "<tr><td colspan='3'><em>No tier-2 records.</em></td></tr>"
        )
        detail_parts.append(
            f"<section><h3><code>{name}</code></h3>"
            "<table><thead><tr><th>Name</th><th>Path</th><th>Reason</th></tr></thead>"
            f"<tbody>{tier2_rows}</tbody></table></section>"
        )
        items = _fleet_pin_items(repo)
        if items:
            pin_rows = "".join(
                "<tr>"
                f"<td>{esc(str(item.get('name') or ''))}</td>"
                f"<td><code>{esc(str(item.get('path') or ''))}</code></td>"
                f"<td>{esc(str(item.get('suggestion') or item.get('pin_state') or ''))}</td>"
                "</tr>"
                for item in items
            )
            pin_parts.append(
                f"<section><h3><code>{name}</code></h3>"
                "<table><thead><tr><th>Name</th><th>Path</th><th>Pin suggestion</th>"
                f"</tr></thead><tbody>{pin_rows}</tbody></table></section>"
            )
    detail_html = "".join(detail_parts) or "<p><em>No repositories.</em></p>"
    pins_html = (
        "".join(pin_parts) or "<p><em>No unpinned MCP launchers across these repositories.</em></p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Auctelis Fleet Agent Reach Report</title>
<style>
body {{ font-family: Georgia, "Times New Roman", serif; margin: 2rem; max-width: 60rem;
  background: linear-gradient(180deg, #f7f4ef 0%, #ebe6dc 100%); color: #1c1917; }}
h1 {{ font-size: 1.75rem; letter-spacing: -0.02em; }}
h3 {{ margin-top: 1.5rem; }}
.banner {{ border-left: 4px solid #b45309; padding: 0.75rem 1rem; background: #fff7ed; margin: 1rem 0; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 0.5rem; }}
td, th {{ border-bottom: 1px solid #d6d3d1; padding: 0.4rem 0.5rem; text-align: left; vertical-align: top; }}
code {{ font-family: ui-monospace, Consolas, monospace; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Auctelis Fleet Agent Reach Report</h1>
<p class="banner">{esc(_DECLARED_ONLY_DISCLAIMER)}</p>
<ul>
<li><strong>Product:</strong> auctelis {esc(str(doc.get("product_version") or product_version()))}</li>
<li><strong>Repositories:</strong> {int(doc.get("repository_count") or 0)}</li>
<li><strong>Reach total:</strong> {int(totals.get("reach_total") or 0)}</li>
<li><strong>Tiers:</strong> tier0={int(totals.get("tier0") or 0)} ·
 tier1={int(totals.get("tier1") or 0)} · tier2={int(totals.get("tier2") or 0)}</li>
<li><strong>Unpinned MCP launchers:</strong> {int(totals.get("unpinned") or 0)}</li>
</ul>
<section>
<h2>Repositories (ranked by tier-2 reach)</h2>
<table>
<thead><tr><th>Repository</th><th>Reach</th><th>tier2</th><th>tier1</th><th>tier0</th><th>Unpinned</th></tr></thead>
<tbody>{summary_rows}</tbody>
</table>
</section>
<section>
<h2>Tier-2 reach by repository</h2>
{detail_html}
</section>
<section>
<h2>Unpinned MCP launchers</h2>
{pins_html}
</section>
{_manual_section_html(doc)}
{_next_step_html(plural=True)}
</body>
</html>
"""


def write_fleet_reach_report_artifacts(
    out_dir: Path,
    entries: Sequence[FleetEntry],
) -> dict[str, Any]:
    """Write the combined fleet ``reach-report.{html,md,json}`` under ``out_dir``."""
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = build_fleet_reach_report(entries)
    write_json(out_dir / "reach-report.json", doc)
    write_text(out_dir / "reach-report.md", render_fleet_reach_md(doc))
    write_text(out_dir / "reach-report.html", render_fleet_reach_html(doc))
    return doc
