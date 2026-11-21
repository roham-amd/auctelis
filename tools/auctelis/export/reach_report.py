"""Shareable Agent Reach Report — HTML / Markdown / JSON + honesty panel.

This is an audit artifact, not a safety certificate. It reuses the check report
and the authority SBOM builder so pilots can forward what ``auctelis check``
already computes.
"""

from __future__ import annotations

import html
import json
import re
import shlex
import urllib.parse
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from auctelis.export.authority_sbom import build_authority_sbom
from auctelis.github_audit import is_owner_repo_slug, safe_git_branch
from auctelis.inventory.coverage import (
    ADAPTER_COVERAGE,
    family_coverage_line_from_coverage,
    truncation_honesty_notes,
)
from auctelis.jsonio import write_json, write_text
from auctelis.security.engine import ScanResult
from auctelis.textutil import (
    escape_markdown_inline,
    markdown_code_span,
    pasteable_code_text,
    sanitize_terminal_line,
    strip_control,
)
from auctelis.versioning import product_version

REPORT_SCHEMA = "auctelis.reach_report.v1"
FLEET_REPORT_SCHEMA = "auctelis.fleet_reach_report.v1"

FleetEntry = tuple[dict[str, Any], ScanResult | None, list[str] | None]

_DECLARED_ONLY_DISCLAIMER = (
    "This report describes DECLARED/CONFIGURED agent authority observed by a "
    "passive scan. It is not a safety certificate, does not prove EFFECTIVE "
    "permissions, and does not establish VERIFIED runtime behavior."
)
# First screen only. The full disclaimer stays under Coverage and limits.
_FIRST_SCREEN_LINE = "Passive scan of declared agent config, not a certificate."

_NEXT_STEP_MD = (
    "_Next step: paste the lockless workflow below (or click **Watch PRs**) to "
    "watch future agent-authority changes in one quiet PR comment._"
)
_NEXT_STEP_MD_NO_WATCH = (
    "_Next step: paste the lockless workflow below to watch future "
    "agent-authority changes in one quiet PR comment._"
)
_NEXT_STEP_MD_PLURAL = (
    "_Next step: paste the lockless workflow below (or click **Watch PRs** per "
    "repo) to watch future agent-authority changes in one quiet PR comment._"
)
_NEXT_STEP_MD_PLURAL_NO_WATCH = (
    "_Next step: paste the lockless workflow below per repo to watch future "
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


@lru_cache(maxsize=1)
def lockless_workflow_yaml() -> str:
    """Release-pinned lockless PR Watch workflow (from packaged template)."""
    path = Path(__file__).resolve().parents[1] / "templates" / "auctelis-diff.yml"
    text = path.read_text(encoding="utf-8")
    pin = f"v{product_version()}"
    # Keep report snippets aligned with the running product version.
    return re.sub(
        r"(uses:\s*roham-amd/auctelis(?:/\.github/actions/auctelis-gate)?@)v[^\s#]+",
        rf"\g<1>{pin}",
        text,
    )


def watch_pr_url(
    *,
    repository: object,
    default_branch: object,
    github_web_base: object = "https://github.com",
    workflow: str | None = None,
) -> str | None:
    """Build a GitHub ``/new/`` URL that pre-fills lockless ``auctelis.yml``."""
    slug = str(repository or "").strip()
    if not is_owner_repo_slug(slug):
        return None
    branch = safe_git_branch(default_branch)
    if not branch:
        return None
    base = str(github_web_base or "https://github.com").rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://"):
        return None
    body = workflow if workflow is not None else lockless_workflow_yaml()
    query = urllib.parse.urlencode(
        {
            "filename": ".github/workflows/auctelis.yml",
            "value": body,
            "message": "Add auctelis lockless PR Watch workflow",
        }
    )
    branch_q = urllib.parse.quote(branch, safe="/")
    return f"{base}/{slug}/new/{branch_q}?{query}"


def _github_api_host(github_web_base: object = "https://github.com") -> str:
    """Derive ``GH_HOST`` for ``gh`` from a web base (github.com or GHES)."""
    base = str(github_web_base or "https://github.com").rstrip("/")
    host = urllib.parse.urlparse(base).hostname or "github.com"
    return host


def org_reusable_caller_yaml(org: str) -> str:
    """Six-line caller workflow for an org-reusable Watch install (AUCT-038)."""
    slug = str(org or "").strip().strip("/")
    return (
        "name: auctelis\n"
        "on: [pull_request]\n"
        "permissions: { contents: read, pull-requests: write }\n"
        "jobs:\n"
        "  auctelis:\n"
        f"    uses: {slug}/.github/.github/workflows/auctelis-org-reusable.yml@main\n"
    )


def build_rollout_watch_prs_script(
    targets: Sequence[str],
    *,
    workflow: str | None = None,
    github_web_base: object = "https://github.com",
    org_reusable: str | None = None,
) -> str:
    """Generate a dry-run-by-default ``gh`` batch Watch-PR shell script (AUCT-035/038)."""
    import base64

    safe_targets = [slug for slug in targets if is_owner_repo_slug(slug)]
    if workflow is not None:
        yaml_text = workflow
    elif org_reusable:
        yaml_text = org_reusable_caller_yaml(org_reusable)
    else:
        yaml_text = lockless_workflow_yaml()
    encoded = base64.b64encode(yaml_text.encode("utf-8")).decode("ascii")
    host = _github_api_host(github_web_base)
    quoted = " ".join(shlex.quote(slug) for slug in safe_targets)
    mode_note = (
        f"# Org-reusable caller → {org_reusable}/.github/.../auctelis-org-reusable.yml@main"
        if org_reusable
        else "# Inline roham-amd/auctelis@vX lockless workflow"
    )
    # APPLY=0 prints planned actions; APPLY=1 opens real PRs via Contents/Pulls API.
    lines = [
        "#!/usr/bin/env bash",
        "# auctelis fleet rollout — lockless Watch PRs (AUCT-035/038)",
        mode_note,
        "# Default: dry-run. Set APPLY=1 to create branches + open PRs.",
        "set -euo pipefail",
        'APPLY="${APPLY:-0}"',
        f'export GH_HOST="{host}"',
        f"TARGETS=({quoted})",
        f'WORKFLOW_B64="{encoded}"',
        'WORKFLOW_PATH=".github/workflows/auctelis.yml"',
        'ALT_WORKFLOW_PATH=".github/workflows/auctelis-gate.yml"',
        'BRANCH="auctelis/watch-prs"',
        'PR_TITLE="Add auctelis lockless PR Watch"',
        'PR_BODY="Install Auctelis lockless PR Watch so future agent-authority changes surface in one quiet PR comment. No AUTHORITY.lock required."',
        "",
        "if ! command -v gh >/dev/null 2>&1; then",
        '  echo "gh CLI required (https://cli.github.com/)" >&2',
        "  exit 2",
        "fi",
        "if ! command -v base64 >/dev/null 2>&1; then",
        '  echo "base64 required" >&2',
        "  exit 2",
        "fi",
        "",
        'if [[ "${#TARGETS[@]}" -eq 0 ]]; then',
        '  echo "No safe unwatched tier-2 targets."',
        "  exit 0",
        "fi",
        "",
        'echo "auctelis rollout-watch-prs · APPLY=${APPLY} · ${#TARGETS[@]} repo(s) · GH_HOST=${GH_HOST}"',
        'for repo in "${TARGETS[@]}"; do',
        '  echo "--- $repo"',
        '  if [[ "$APPLY" != "1" ]]; then',
        '    echo "Would open Watch PR for $repo (set APPLY=1 to create)"',
        "    continue",
        "  fi",
        '  default_branch="$(gh api "repos/$repo" --jq .default_branch)"',
        '  sha="$(gh api "repos/$repo/git/ref/heads/${default_branch}" --jq .object.sha)"',
        '  if gh api "repos/$repo/contents/${WORKFLOW_PATH}" --jq .sha >/dev/null 2>&1 \\',
        '    || gh api "repos/$repo/contents/${ALT_WORKFLOW_PATH}" --jq .sha >/dev/null 2>&1; then',
        '    echo "Skip $repo — auctelis.yml or auctelis-gate.yml already present"',
        "    continue",
        "  fi",
        '  if ! gh api "repos/$repo/git/ref/heads/${BRANCH}" >/dev/null 2>&1; then',
        '    gh api -X POST "repos/$repo/git/refs" \\',
        '      -f ref="refs/heads/${BRANCH}" -f sha="$sha" >/dev/null',
        "  fi",
        '  if ! gh api -X PUT "repos/$repo/contents/${WORKFLOW_PATH}" \\',
        '      -f message="Add auctelis lockless PR Watch workflow" \\',
        '      -f content="$WORKFLOW_B64" \\',
        '      -f branch="$BRANCH" >/dev/null; then',
        '    echo "Failed to write workflow for $repo — if HTTP 403/422, run: gh auth refresh -s workflow" >&2',
        "    continue",
        "  fi",
        '  if ! gh api -X POST "repos/$repo/pulls" \\',
        '      -f title="$PR_TITLE" \\',
        '      -f head="$BRANCH" \\',
        '      -f base="$default_branch" \\',
        '      -f body="$PR_BODY" --jq .html_url; then',
        '    echo "Failed to open PR for $repo — if HTTP 403/422, run: gh auth refresh -s workflow" >&2',
        "    continue",
        "  fi",
        "done",
        "",
    ]
    return "\n".join(lines)


def _workflow_snippet_md() -> list[str]:
    yaml_text = lockless_workflow_yaml().rstrip()
    return [
        "## Lockless PR Watch workflow",
        "",
        "Copy into `.github/workflows/auctelis.yml` (or use **Watch PRs** when linked):",
        "",
        "```yaml",
        yaml_text,
        "```",
        "",
    ]


def _workflow_snippet_html() -> str:
    esc = html.escape
    yaml_text = lockless_workflow_yaml().rstrip()
    return (
        "<section><h2>Lockless PR Watch workflow</h2>"
        "<p>Copy into <code>.github/workflows/auctelis.yml</code> "
        "(or use <strong>Watch PRs</strong> when linked):</p>"
        f"<pre><code>{esc(yaml_text)}</code></pre></section>"
    )


def _watch_link_md(doc: dict[str, Any]) -> str:
    slug = str(doc.get("repository") or "")
    if doc.get("already_watching"):
        return f"**Watching** `{escape_markdown_inline(slug)}`" if slug else "**Watching**"
    url = watch_pr_url(
        repository=doc.get("repository"),
        default_branch=doc.get("default_branch"),
        github_web_base=doc.get("github_web_base") or "https://github.com",
    )
    if not url:
        return ""
    return f"[Watch PRs in {escape_markdown_inline(slug)}]({url})"


def _watch_link_html(doc: dict[str, Any]) -> str:
    esc = html.escape
    slug = esc(str(doc.get("repository") or ""))
    if doc.get("already_watching"):
        label = f"<code>{slug}</code>" if slug else ""
        return f"<p><strong>Watching</strong> {label}</p>"
    url = watch_pr_url(
        repository=doc.get("repository"),
        default_branch=doc.get("default_branch"),
        github_web_base=doc.get("github_web_base") or "https://github.com",
    )
    if not url:
        return ""
    return f'<p><a href="{esc(url, quote=True)}"><strong>Watch PRs in {slug}</strong></a></p>'


def _fleet_honesty_notes(doc: dict[str, Any]) -> list[str]:
    notes = [str(n) for n in _as_list(doc.get("honesty_notes")) if str(n)]
    if notes:
        return notes
    return [str(n) for n in _as_list(_as_dict(doc.get("honesty")).get("notes")) if str(n)]


def _skipped_section_md(
    skipped: Sequence[Any],
    honesty_notes: Sequence[str],
) -> list[str]:
    rows = [row for row in skipped if isinstance(row, dict)]
    if not rows and not honesty_notes:
        return []
    lines = ["## Skipped / Incomplete repositories", ""]
    if honesty_notes:
        for note in honesty_notes:
            lines.append(f"- {escape_markdown_inline(str(note), max_len=300)}")
        lines.append("")
    for row in rows:
        repo = escape_markdown_inline(str(row.get("repository") or "?"), max_len=120)
        note_bits = [str(n) for n in _as_list(row.get("notes")) if str(n)]
        detail = escape_markdown_inline("; ".join(note_bits) or "skipped", max_len=300)
        flag = "truncated" if row.get("truncated") else "skipped"
        lines.append(f"- **{repo}** ({flag}) — {detail}")
    if rows:
        lines.append("")
    return lines


def _skipped_section_html(
    skipped: Sequence[Any],
    honesty_notes: Sequence[str],
) -> str:
    rows = [row for row in skipped if isinstance(row, dict)]
    if not rows and not honesty_notes:
        return ""
    esc = html.escape
    parts = ["<section><h2>Skipped / Incomplete repositories</h2><ul>"]
    for note in honesty_notes:
        parts.append(f"<li>{esc(str(note))}</li>")
    for row in rows:
        repo = esc(str(row.get("repository") or "?"))
        note_bits = [str(n) for n in _as_list(row.get("notes")) if str(n)]
        detail = esc("; ".join(note_bits) or "skipped")
        flag = "truncated" if row.get("truncated") else "skipped"
        parts.append(f"<li><strong><code>{repo}</code></strong> ({flag}) — {detail}</li>")
    parts.append("</ul></section>")
    return "".join(parts)


def _next_step_html(*, plural: bool, has_watch: bool = True) -> str:
    where = "each repository" if plural else "this repository"
    click = " (or click <strong>Watch PRs</strong>)" if has_watch else ""
    return (
        "<footer><p><strong>Next step:</strong> paste the lockless workflow"
        f"{click} in {where} to watch future "
        "agent-authority changes in one quiet PR comment.</p></footer>"
    )


def _next_step_md(*, plural: bool, has_watch: bool) -> str:
    if plural:
        return _NEXT_STEP_MD_PLURAL if has_watch else _NEXT_STEP_MD_PLURAL_NO_WATCH
    return _NEXT_STEP_MD if has_watch else _NEXT_STEP_MD_NO_WATCH


def _doc_has_watch_cta(doc: dict[str, Any]) -> bool:
    if doc.get("already_watching"):
        return True
    return bool(
        watch_pr_url(
            repository=doc.get("repository"),
            default_branch=doc.get("default_branch"),
            github_web_base=doc.get("github_web_base") or "https://github.com",
        )
    )


def _manual_section_html(doc: dict[str, Any], *, heading: str = "h3") -> str:
    esc = html.escape
    tag = "h2" if heading == "h2" else "h3"
    rows = _manual_family_rows(doc)
    if not _as_dict(doc.get("coverage")):
        return (
            f"<{tag}>Not auto-inspected</{tag}>"
            "<p><em>Coverage metadata unavailable for this report.</em></p>"
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
        f"<{tag}>Not auto-inspected</{tag}><ul>"
        + items
        + "</ul><p>These families have no passive discovery adapter; "
        "they require manual review.</p>"
    )


def _pin_item_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in _as_list(_as_dict(doc.get("pins")).get("items")) if isinstance(item, dict)
    ]


def _tier2_from_reach(reach: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = _as_list(reach.get("records")) or _as_list(reach.get("top"))
    return [item for item in ranked if isinstance(item, dict) and int(item.get("tier") or 0) >= 2]


def _config_snippet_for(item: dict[str, Any], pins: Sequence[dict[str, Any]]) -> str:
    name = str(item.get("name") or "")
    path = str(item.get("path") or "")
    for pin in pins:
        if str(pin.get("name") or "") != name:
            continue
        pin_path = str(pin.get("path") or "")
        if path and pin_path and pin_path != path:
            continue
        return str(pin.get("config_snippet") or "").strip()
    return ""


def _pin_fix_md(snippet: str) -> str:
    span = markdown_code_span(snippet) if snippet else None
    if not span:
        return ""
    return f"**Pin fix:** {span}"


def _pin_fix_html(snippet: str) -> str:
    text = pasteable_code_text(snippet) if snippet else None
    if not text:
        return ""
    return f"<strong>Pin fix:</strong> <code>{html.escape(text)}</code>"


def _summary_warning_text(notes: Sequence[Any]) -> str:
    for note in notes:
        text = str(note).strip()
        if text:
            return text
    return ""


def _top_findings_md(
    rows: Sequence[tuple[dict[str, Any], Sequence[dict[str, Any]], str]],
) -> list[str]:
    """``(record, pin items, repo label)`` — label is empty for a single repo."""
    if not rows:
        return ["_No tier-2 records in this inventory._"]
    lines: list[str] = []
    for item, pins, repo_label in list(rows)[:3]:
        name = escape_markdown_inline(str(item.get("name") or ""), max_len=160)
        path = _md_code(item.get("path"))
        reason = escape_markdown_inline(
            str(item.get("reason") or item.get("card") or ""), max_len=200
        )
        where = f"in {repo_label} " if repo_label else ""
        lines.append(f"- **{name}** {where}({path}) — {reason}")
        fix = _pin_fix_md(_config_snippet_for(item, list(pins)))
        if fix:
            lines.append(f"  {fix}")
    return lines


def _top_findings_html(
    rows: Sequence[tuple[dict[str, Any], Sequence[dict[str, Any]], str]],
) -> str:
    if not rows:
        return "<p><em>No tier-2 records in this inventory.</em></p>"
    parts: list[str] = ["<ol>"]
    for item, pins, repo_label in list(rows)[:3]:
        name = html.escape(str(item.get("name") or ""))
        path = html.escape(str(item.get("path") or ""))
        reason = html.escape(str(item.get("reason") or item.get("card") or ""))
        where = f" in <code>{html.escape(repo_label)}</code>" if repo_label else ""
        fix = _pin_fix_html(_config_snippet_for(item, list(pins)))
        fix_html = f" {fix}" if fix else ""
        parts.append(
            f"<li><strong>{name}</strong>{where} (<code>{path}</code>) — {reason}{fix_html}</li>"
        )
    parts.append("</ol>")
    return "".join(parts)


def _unpinned_md_line(item: dict[str, Any]) -> str:
    suggestion = str(item.get("suggestion") or item.get("pin_state") or "")
    snippet = str(item.get("config_snippet") or "").strip()
    prose = escape_markdown_inline(suggestion, max_len=160) if suggestion else ""
    fix = _pin_fix_md(snippet)
    head = f"- {_md_code(item.get('name'))} ({_md_code(item.get('path'))})"
    if prose and fix:
        return f"{head} — {prose} {fix}"
    if fix:
        return f"{head} — {fix}"
    if prose:
        return f"{head} — {prose}"
    return head


def _unpinned_html_cell(item: dict[str, Any]) -> str:
    suggestion = str(item.get("suggestion") or item.get("pin_state") or "")
    snippet = str(item.get("config_snippet") or "").strip()
    prose = html.escape(suggestion) if suggestion else ""
    fix = _pin_fix_html(snippet)
    if prose and fix:
        return f"{prose} {fix}"
    return fix or prose


def _coverage_limits_md(doc: dict[str, Any]) -> list[str]:
    honesty = _as_dict(doc.get("honesty"))
    lines = ["## Coverage and limits", "", "### Honesty", ""]
    lines.append(str(honesty.get("disclaimer") or _DECLARED_ONLY_DISCLAIMER))
    lines.append("")
    coverage_line = str(honesty.get("coverage_line") or "").strip()
    if coverage_line:
        lines.append(f"- **Coverage:** {coverage_line}")
    trunc = _as_list(honesty.get("truncation")) or _as_list(honesty.get("notes"))
    if trunc:
        for note in trunc:
            lines.append(f"- {note}")
    else:
        lines.append("- No walk truncation reported for this scan.")
    lines.append("- Inventory is DECLARED/CONFIGURED only.")
    lines.append("")
    manual = _manual_md_lines(doc)
    if manual and manual[0].startswith("## "):
        manual = ["### " + manual[0][3:], *manual[1:]]
    lines.extend(manual)
    return lines


def _coverage_limits_html(doc: dict[str, Any]) -> str:
    esc = html.escape
    honesty = _as_dict(doc.get("honesty"))
    disclaimer = str(honesty.get("disclaimer") or _DECLARED_ONLY_DISCLAIMER)
    coverage_line = str(honesty.get("coverage_line") or "").strip()
    coverage_html = (
        f"<li><strong>Coverage:</strong> {esc(coverage_line)}</li>" if coverage_line else ""
    )
    trunc = _as_list(honesty.get("truncation")) or _as_list(honesty.get("notes"))
    if trunc:
        items = "".join(f"<li>{esc(str(note))}</li>" for note in trunc)
    else:
        items = "<li>No walk truncation reported for this scan.</li>"
    return (
        "<section><h2>Coverage and limits</h2>"
        "<h3>Honesty</h3>"
        f"<p>{esc(disclaimer)}</p>"
        f"<ul>{coverage_html}{items}<li>Inventory is DECLARED/CONFIGURED only.</li></ul>"
        + _manual_section_html(doc)
        + "</section>"
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
    truncation = list(truncation_honesty_notes(coverage))
    extra_notes = [str(n) for n in _as_list(report.get("honesty_notes")) if str(n).strip()]
    # GitHub tree truncation / fetch notes land in honesty_notes; surface them
    # in the same Honesty panel as walk-cap truncation (AUCT-027).
    seen_trunc = set(truncation)
    for note in extra_notes:
        if note not in seen_trunc:
            truncation.append(note)
            seen_trunc.add(note)
    honesty = {
        "disclaimer": _DECLARED_ONLY_DISCLAIMER,
        "coverage_line": coverage_line,
        "truncation": truncation,
        "notes": extra_notes,
        "unparsed": unparsed,
        "declared_only": True,
    }
    reach = _as_dict(report.get("reach"))
    doc: dict[str, Any] = {
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
    if report.get("default_branch"):
        doc["default_branch"] = str(report.get("default_branch"))
    if report.get("github_web_base"):
        doc["github_web_base"] = str(report.get("github_web_base"))
    if report.get("already_watching") is not None:
        doc["already_watching"] = bool(report.get("already_watching"))
    return doc


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
    """Render a Markdown reach report suitable for tickets / PRs.

    The first screen is the finding: tier counts and the top tier-2 records.
    Honesty and blind spots stay, under Coverage and limits, after the cards.
    """
    honesty = _as_dict(doc.get("honesty"))
    reach = _as_dict(doc.get("reach"))
    tiers = _as_dict(reach.get("tier_counts"))
    tier2 = _tier2_from_reach(reach)
    pins = _pin_item_rows(doc)
    total = int(reach.get("total") or 0)
    tier2_n = int(tiers.get("tier2") or 0)
    lines: list[str] = [
        "# Auctelis Agent Reach Report",
        "",
        f"> {_FIRST_SCREEN_LINE}",
        "",
        "## Summary",
        "",
        (
            f"**{total} records, {tier2_n} at tier 2.** "
            f"tier0={int(tiers.get('tier0') or 0)} · "
            f"tier1={int(tiers.get('tier1') or 0)} · tier2={tier2_n}"
        ),
        "",
    ]
    lines.extend(_top_findings_md([(item, pins, "") for item in tier2]))
    warning = _summary_warning_text(_as_list(honesty.get("truncation")))
    if warning:
        lines.extend(["", f"**Warning:** {escape_markdown_inline(warning, max_len=300)}"])
    lines.extend(
        [
            "",
            f"- **Product:** auctelis {doc.get('product_version') or product_version()}",
            f"- **Repository:** `{doc.get('repository') or ''}`",
            "",
            "## Tier-2 reach",
            "",
        ]
    )
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
    if pins:
        lines.extend(["", "## Unpinned MCP launchers", ""])
        for item in pins:
            lines.append(_unpinned_md_line(item))
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
    lines.extend(["", *_coverage_limits_md(doc)])
    lines.extend(_workflow_snippet_md())
    watch = _watch_link_md(doc)
    if watch:
        lines.extend([watch, ""])
    lines.extend([_next_step_md(plural=False, has_watch=_doc_has_watch_cta(doc)), ""])
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

    pins_doc = _as_dict(doc.get("pins"))
    unpinned_items = [item for item in _as_list(pins_doc.get("items")) if isinstance(item, dict)]
    if unpinned_items:
        pin_rows = "".join(
            "<tr>"
            f"<td>{esc(str(item.get('name') or ''))}</td>"
            f"<td><code>{esc(str(item.get('path') or ''))}</code></td>"
            f"<td>{_unpinned_html_cell(item)}</td>"
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

    watch_html = _watch_link_html(doc)
    has_watch = _doc_has_watch_cta(doc)
    tier2_n = int(tiers.get("tier2") or 0)
    total_n = int(reach.get("total") or 0)
    summary_findings = _top_findings_html(
        [(item, unpinned_items, "") for item in _tier2_from_reach(reach)]
    )
    warning = _summary_warning_text(_as_list(honesty.get("truncation")))
    warning_html = (
        f'<p class="warning"><strong>Warning:</strong> {esc(warning)}</p>' if warning else ""
    )
    summary_html = (
        "<section><h2>Summary</h2>"
        f"<p><strong>{total_n} records, {tier2_n} at tier 2.</strong> "
        f"tier0={int(tiers.get('tier0') or 0)} · "
        f"tier1={int(tiers.get('tier1') or 0)} · tier2={tier2_n}</p>"
        f"{summary_findings}{warning_html}</section>"
    )
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
pre {{ background: #f5f5f4; padding: 0.75rem 1rem; overflow-x: auto; }}
</style>
</head>
<body>
<h1>Auctelis Agent Reach Report</h1>
<p class="banner">{esc(_FIRST_SCREEN_LINE)}</p>
{summary_html}
<ul>
<li><strong>Product:</strong> auctelis {esc(str(doc.get("product_version") or product_version()))}</li>
<li><strong>Repository:</strong> <code>{esc(str(doc.get("repository") or ""))}</code></li>
</ul>
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
{pins_section}
{baseline_section}
{_coverage_limits_html(doc)}
{_workflow_snippet_html()}
{watch_html}
{_next_step_html(plural=False, has_watch=has_watch)}
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


def build_fleet_reach_report(
    entries: Sequence[FleetEntry],
    *,
    skipped: Sequence[dict[str, Any]] | None = None,
    honesty_notes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Assemble one ranked fleet document from several single-repo reports.

    ``entries`` is ``(check_report, scan, cards)`` per repository, exactly the
    shape ``build_check_report`` returns. Repositories are ranked by tier-2
    reach so the most dangerous repo appears first.
    """
    repositories: list[dict[str, Any]] = []
    manual: list[str] = []
    totals = {
        "reach_total": 0,
        "tier0": 0,
        "tier1": 0,
        "tier2": 0,
        "unpinned": 0,
        "watching": 0,
        "unwatched_tier2": 0,
    }
    for report, scan, cards in entries:
        doc = build_reach_report(report, scan, cards=cards)
        repositories.append(doc)
        reach = _as_dict(doc.get("reach"))
        tiers = _as_dict(reach.get("tier_counts"))
        totals["reach_total"] += int(reach.get("total") or 0)
        for tier_key in ("tier0", "tier1", "tier2"):
            totals[tier_key] += int(tiers.get(tier_key) or 0)
        totals["unpinned"] += int(_as_dict(doc.get("pins")).get("unpinned") or 0)
        watching = bool(doc.get("already_watching"))
        if watching:
            totals["watching"] += 1
        elif int(tiers.get("tier2") or 0) > 0:
            totals["unwatched_tier2"] += 1
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
    skipped_rows = [row for row in (skipped or []) if isinstance(row, dict)]
    notes = [str(n) for n in (honesty_notes or []) if str(n)]
    out: dict[str, Any] = {
        "schema": FLEET_REPORT_SCHEMA,
        "product": "auctelis",
        "product_version": product_version(),
        "honesty": {
            "disclaimer": _DECLARED_ONLY_DISCLAIMER,
            "declared_only": True,
            "manual_review_families": manual,
            "notes": notes,
        },
        # Fleet-level coverage block so shared renderers can list blind spots.
        "coverage": {"manual_review_families": manual} if manual else {},
        "repository_count": len(repositories),
        "totals": totals,
        "repositories": repositories,
    }
    if skipped_rows:
        out["skipped"] = skipped_rows
    if notes:
        out["honesty_notes"] = notes
    return out


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


def _unwatched_tier2_slugs(doc: dict[str, Any], *, limit: int = 10) -> list[str]:
    """Top unwatched tier-2 repo slugs (safe owner/repo only)."""
    out: list[str] = []
    for repo in _fleet_repo_table_rows(doc):
        if repo.get("already_watching"):
            continue
        tiers = _as_dict(_as_dict(repo.get("reach")).get("tier_counts"))
        if int(tiers.get("tier2") or 0) <= 0:
            continue
        slug = str(repo.get("repository") or "").strip()
        if not is_owner_repo_slug(slug):
            continue
        out.append(slug)
        if len(out) >= limit:
            break
    return out


def _fleet_github_web_base(doc: dict[str, Any]) -> str:
    for repo in _fleet_repo_table_rows(doc):
        base = str(repo.get("github_web_base") or "").strip()
        if base:
            return base
    return "https://github.com"


def _org_rollout_md(doc: dict[str, Any], *, org_reusable: str | None = None) -> list[str]:
    """Org-reusable caller + dry-run ``rollout-watch-prs.sh`` (AUCT-032/035/038)."""
    targets = _unwatched_tier2_slugs(doc, limit=10)
    org_label = str(org_reusable or "YOUR_ORG").strip() or "YOUR_ORG"
    lines = [
        "## Org rollout (5+ repos)",
        "",
        "Place [`docs/auctelis-org-reusable.yml`](https://github.com/roham-amd/auctelis/blob/main/docs/auctelis-org-reusable.yml) "
        "in your org `.github` repository, then each app repo calls:",
        "",
        "```yaml",
        "jobs:",
        "  auctelis:",
        f"    uses: {org_label}/.github/.github/workflows/auctelis-org-reusable.yml@main",
        "```",
        "",
    ]
    if not targets:
        lines.extend(
            [
                "_No unwatched tier-2 repositories in this fleet — nothing to batch-open._",
                "",
            ]
        )
        return lines
    script = build_rollout_watch_prs_script(
        targets,
        github_web_base=_fleet_github_web_base(doc),
        org_reusable=org_reusable,
    )
    lines.extend(
        [
            "Or open lockless Watch PRs for the top unwatched tier-2 repos "
            "with the generated `rollout-watch-prs.sh` (defaults to dry-run; "
            "`APPLY=1` creates branches and opens PRs):",
            "",
            "```bash",
            script.rstrip(),
            "```",
            "",
            "```bash",
            "bash rollout-watch-prs.sh          # dry-run (APPLY=0)",
            "APPLY=1 bash rollout-watch-prs.sh  # open Watch PRs",
            "```",
            "",
        ]
    )
    return lines


def _org_rollout_html(doc: dict[str, Any], *, org_reusable: str | None = None) -> str:
    esc = html.escape
    targets = _unwatched_tier2_slugs(doc, limit=10)
    org_label = str(org_reusable or "YOUR_ORG").strip() or "YOUR_ORG"
    snippet = (
        "jobs:\n  auctelis:\n"
        f"    uses: {org_label}/.github/.github/workflows/auctelis-org-reusable.yml@main"
    )
    body_parts = [
        "<p>Place <code>docs/auctelis-org-reusable.yml</code> in your org "
        "<code>.github</code> repository, then each app repo calls:</p>",
        f"<pre><code>{esc(snippet)}</code></pre>",
    ]
    if not targets:
        body_parts.append(
            "<p><em>No unwatched tier-2 repositories in this fleet — "
            "nothing to batch-open.</em></p>"
        )
    else:
        script = build_rollout_watch_prs_script(
            targets,
            github_web_base=_fleet_github_web_base(doc),
            org_reusable=org_reusable,
        )
        howto = (
            "bash rollout-watch-prs.sh          # dry-run (APPLY=0)\n"
            "APPLY=1 bash rollout-watch-prs.sh  # open Watch PRs"
        )
        body_parts.extend(
            [
                "<p>Or open lockless Watch PRs for the top unwatched tier-2 repos "
                "with the generated <code>rollout-watch-prs.sh</code> "
                "(defaults to dry-run; <code>APPLY=1</code> creates branches "
                "and opens PRs):</p>",
                f"<pre><code>{esc(script)}</code></pre>",
                f"<pre><code>{esc(howto)}</code></pre>",
            ]
        )
    inner = "".join(body_parts)
    return (
        "<section><details><summary><strong>Org rollout (5+ repos)</strong></summary>"
        f"{inner}</details></section>"
    )


def render_fleet_summary(doc: dict[str, Any]) -> str:
    """Compact terminal summary for a multi-repo ``check --report`` run."""
    totals = _as_dict(doc.get("totals"))
    repo_n = int(doc.get("repository_count") or 0)
    lines = [
        (f"auctelis check · fleet reach report · {repo_n} repositories"),
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
        f"Watching: {int(totals.get('watching') or 0)} of {repo_n} repos",
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


def render_fleet_reach_md(doc: dict[str, Any], *, org_reusable: str | None = None) -> str:
    """Render the fleet reach report as Markdown (shareable in tickets)."""
    totals = _as_dict(doc.get("totals"))
    repositories = _fleet_repo_table_rows(doc)
    skipped = [row for row in _as_list(doc.get("skipped")) if isinstance(row, dict)]
    honesty_notes = _fleet_honesty_notes(doc)
    org = org_reusable if org_reusable is not None else doc.get("org_reusable")
    org = str(org).strip() if org else None
    repo_n = int(doc.get("repository_count") or 0)
    tier2_n = int(totals.get("tier2") or 0)
    repo_word = "repository" if repo_n == 1 else "repositories"
    finding_rows: list[tuple[dict[str, Any], list[dict[str, Any]], str]] = []
    for repo in repositories:
        pins = _fleet_pin_items(repo)
        label = _md_code(repo.get("repository"))
        for item in _tier2_records(repo):
            finding_rows.append((item, pins, label))
    trunc_notes: list[str] = []
    for note in honesty_notes:
        if "truncat" in str(note).lower():
            trunc_notes.append(str(note))
    for row in skipped:
        if row.get("truncated"):
            trunc_notes.extend(
                str(note) for note in _as_list(row.get("notes")) if str(note).strip()
            )
    lines: list[str] = [
        "# Auctelis Fleet Agent Reach Report",
        "",
        f"> {_FIRST_SCREEN_LINE}",
        "",
        "## Summary",
        "",
        (
            f"**{repo_n} {repo_word}, {tier2_n} at tier 2.** "
            f"tier0={int(totals.get('tier0') or 0)} · "
            f"tier1={int(totals.get('tier1') or 0)} · tier2={tier2_n}"
        ),
        (
            f"- **Watching:** {int(totals.get('watching') or 0)} of {repo_n} repos · "
            f"unwatched tier-2: {int(totals.get('unwatched_tier2') or 0)}"
        ),
        "",
    ]
    lines.extend(_top_findings_md(finding_rows))
    warning = _summary_warning_text(trunc_notes)
    if warning:
        lines.extend(["", f"**Warning:** {escape_markdown_inline(warning, max_len=300)}"])
    if _unwatched_tier2_slugs(doc, limit=1):
        lines.extend(
            [
                "",
                "Open Watch PRs: `bash rollout-watch-prs.sh` (dry-run), "
                "then `APPLY=1 bash rollout-watch-prs.sh`.",
            ]
        )
    lines.extend(
        [
            "",
            f"- **Product:** auctelis {doc.get('product_version') or product_version()}",
            f"- **Unpinned MCP launchers:** {int(totals.get('unpinned') or 0)}",
            "",
            "### Repositories (ranked by tier-2 reach)",
            "",
            "| Repository | Reach | tier2 | tier1 | tier0 | Unpinned | Watch |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for repo in repositories:
        reach = _as_dict(repo.get("reach"))
        tiers = _as_dict(reach.get("tier_counts"))
        watch = _watch_link_md(repo) or "—"
        lines.append(
            f"| {_md_code(repo.get('repository'))} | "
            f"{int(reach.get('total') or 0)} | {int(tiers.get('tier2') or 0)} | "
            f"{int(tiers.get('tier1') or 0)} | {int(tiers.get('tier0') or 0)} | "
            f"{int(_as_dict(repo.get('pins')).get('unpinned') or 0)} | {watch} |"
        )
    lines.extend(["", *_org_rollout_md(doc, org_reusable=org)])
    lines.extend(["## Tier-2 reach by repository", ""])
    any_tier2 = False
    for repo in repositories:
        tier2 = _tier2_records(repo)
        lines.append(f"### {_md_code(repo.get('repository'))}")
        lines.append("")
        watch = _watch_link_md(repo)
        if watch:
            lines.append(watch)
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
            lines.append(_unpinned_md_line(item))
        lines.append("")
    if not any_pins:
        lines.extend(["_No unpinned MCP launchers across these repositories._", ""])
    lines.extend(_skipped_section_md(skipped, honesty_notes))
    lines.extend(_coverage_limits_md(doc))
    lines.extend(_workflow_snippet_md())
    fleet_has_watch = any(_doc_has_watch_cta(repo) for repo in repositories) or bool(
        _unwatched_tier2_slugs(doc, limit=1)
    )
    lines.extend([_next_step_md(plural=True, has_watch=fleet_has_watch), ""])
    return "\n".join(lines)


def render_fleet_reach_html(doc: dict[str, Any], *, org_reusable: str | None = None) -> str:
    """Render the fleet reach report as one self-contained HTML file."""
    esc = html.escape
    totals = _as_dict(doc.get("totals"))
    repositories = _fleet_repo_table_rows(doc)
    skipped = [row for row in _as_list(doc.get("skipped")) if isinstance(row, dict)]
    honesty_notes = _fleet_honesty_notes(doc)
    org = org_reusable if org_reusable is not None else doc.get("org_reusable")
    org = str(org).strip() if org else None

    def _watch_cell(repo: dict[str, Any]) -> str:
        if repo.get("already_watching"):
            return "<strong>Watching</strong>"
        url = watch_pr_url(
            repository=repo.get("repository"),
            default_branch=repo.get("default_branch"),
            github_web_base=repo.get("github_web_base") or "https://github.com",
        )
        if not url:
            return "—"
        return f'<a href="{esc(url, quote=True)}">Watch PRs</a>'

    summary_rows = (
        "".join(
            "<tr>"
            f"<td><code>{esc(str(repo.get('repository') or ''))}</code></td>"
            f"<td>{int(_as_dict(repo.get('reach')).get('total') or 0)}</td>"
            f"<td>{int(_as_dict(_as_dict(repo.get('reach')).get('tier_counts')).get('tier2') or 0)}</td>"
            f"<td>{int(_as_dict(_as_dict(repo.get('reach')).get('tier_counts')).get('tier1') or 0)}</td>"
            f"<td>{int(_as_dict(_as_dict(repo.get('reach')).get('tier_counts')).get('tier0') or 0)}</td>"
            f"<td>{int(_as_dict(repo.get('pins')).get('unpinned') or 0)}</td>"
            f"<td>{_watch_cell(repo)}</td>"
            "</tr>"
            for repo in repositories
        )
        or "<tr><td colspan='7'><em>No repositories.</em></td></tr>"
    )

    detail_parts: list[str] = []
    pin_parts: list[str] = []
    for repo in repositories:
        name = esc(str(repo.get("repository") or ""))
        watch_html = _watch_link_html(repo)
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
            f"<section><h3><code>{name}</code></h3>{watch_html}"
            "<table><thead><tr><th>Name</th><th>Path</th><th>Reason</th></tr></thead>"
            f"<tbody>{tier2_rows}</tbody></table></section>"
        )
        items = _fleet_pin_items(repo)
        if items:
            pin_rows = "".join(
                "<tr>"
                f"<td>{esc(str(item.get('name') or ''))}</td>"
                f"<td><code>{esc(str(item.get('path') or ''))}</code></td>"
                f"<td>{_unpinned_html_cell(item)}</td>"
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
    skipped_html = _skipped_section_html(skipped, honesty_notes)
    repo_n = int(doc.get("repository_count") or 0)
    tier2_n = int(totals.get("tier2") or 0)
    repo_word = "repository" if repo_n == 1 else "repositories"
    finding_rows: list[tuple[dict[str, Any], list[dict[str, Any]], str]] = []
    for repo in repositories:
        pins = _fleet_pin_items(repo)
        label = str(repo.get("repository") or "")
        for item in _tier2_records(repo):
            finding_rows.append((item, pins, label))
    trunc_notes = [str(note) for note in honesty_notes if "truncat" in str(note).lower()]
    for row in skipped:
        if row.get("truncated"):
            trunc_notes.extend(
                str(note) for note in _as_list(row.get("notes")) if str(note).strip()
            )
    warning = _summary_warning_text(trunc_notes)
    warning_html = (
        f'<p class="warning"><strong>Warning:</strong> {esc(warning)}</p>' if warning else ""
    )
    rollout_html = ""
    if _unwatched_tier2_slugs(doc, limit=1):
        rollout_html = (
            "<p>Open Watch PRs: <code>bash rollout-watch-prs.sh</code> (dry-run), "
            "then <code>APPLY=1 bash rollout-watch-prs.sh</code>.</p>"
        )
    summary_html = (
        "<section><h2>Summary</h2>"
        f"<p><strong>{repo_n} {repo_word}, {tier2_n} at tier 2.</strong> "
        f"tier0={int(totals.get('tier0') or 0)} · "
        f"tier1={int(totals.get('tier1') or 0)} · tier2={tier2_n}</p>"
        "<ul>"
        f"<li><strong>Watching:</strong> {int(totals.get('watching') or 0)} of {repo_n} "
        f"repos · unwatched tier-2: {int(totals.get('unwatched_tier2') or 0)}</li>"
        f"<li><strong>Unpinned MCP launchers:</strong> {int(totals.get('unpinned') or 0)}</li>"
        "</ul>"
        f"{_top_findings_html(finding_rows)}{warning_html}{rollout_html}"
        "<h3>Repositories (ranked by tier-2 reach)</h3>"
        "<table><thead><tr><th>Repository</th><th>Reach</th><th>tier2</th><th>tier1</th>"
        f"<th>tier0</th><th>Unpinned</th><th>Watch</th></tr></thead><tbody>{summary_rows}</tbody></table>"
        "</section>"
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
pre {{ background: #f5f5f4; padding: 0.75rem 1rem; overflow-x: auto; }}
</style>
</head>
<body>
<h1>Auctelis Fleet Agent Reach Report</h1>
<p class="banner">{esc(_FIRST_SCREEN_LINE)}</p>
{summary_html}
<p><strong>Product:</strong> auctelis {esc(str(doc.get("product_version") or product_version()))}</p>
{_org_rollout_html(doc, org_reusable=org)}
<section>
<h2>Tier-2 reach by repository</h2>
{detail_html}
</section>
<section>
<h2>Unpinned MCP launchers</h2>
{pins_html}
</section>
{skipped_html}
{_coverage_limits_html(doc)}
{_workflow_snippet_html()}
{_next_step_html(plural=True, has_watch=any(_doc_has_watch_cta(r) for r in repositories) or bool(_unwatched_tier2_slugs(doc, limit=1)))}
</body>
</html>
"""


def write_fleet_reach_report_artifacts(
    out_dir: Path,
    entries: Sequence[FleetEntry],
    *,
    skipped: Sequence[dict[str, Any]] | None = None,
    honesty_notes: Sequence[str] | None = None,
    org_reusable: str | None = None,
) -> dict[str, Any]:
    """Write the combined fleet ``reach-report.{html,md,json}`` under ``out_dir``."""
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = build_fleet_reach_report(
        entries,
        skipped=skipped,
        honesty_notes=honesty_notes,
    )
    org = str(org_reusable or "").strip() or None
    if org:
        doc["org_reusable"] = org
    write_json(out_dir / "reach-report.json", doc)
    write_text(out_dir / "reach-report.md", render_fleet_reach_md(doc, org_reusable=org))
    write_text(out_dir / "reach-report.html", render_fleet_reach_html(doc, org_reusable=org))
    targets = _unwatched_tier2_slugs(doc, limit=10)
    if targets:
        script = build_rollout_watch_prs_script(
            targets,
            github_web_base=_fleet_github_web_base(doc),
            org_reusable=org,
        )
        write_text(out_dir / "rollout-watch-prs.sh", script)
    return doc
