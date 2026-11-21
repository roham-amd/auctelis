"""Compact Authority Diff PR comment (≤12 lines).

One verdict, at most five risk-ranked authority cards, the unknowns (including
``NOT PARSED``), and the required action. Finding IDs and rule IDs stay in the
artifacts, not the review UI. Target-derived strings are escaped so findings
cannot inject markdown links/mentions.
"""

from __future__ import annotations

import re
from typing import Any

from auctelis.authority_card import (
    delta_cards,
    is_unpinned_mcp,
    pin_config_snippet,
)
from auctelis.authority_lock import delta_label
from auctelis.security.authority import render_component_delta_lines
from auctelis.security.gating import is_gate_finding
from auctelis.textutil import (
    escape_markdown,
    markdown_code_span,
    sanitize_terminal_text,
)

__all__ = [
    "AUCTELIS_COMMENT_MARKER",
    "escape_markdown",
    "render_authority_diff_comment",
    "render_first_run_comment",
    "render_gate_pr_comment",
]

_SEV_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}

# Sticky-comment marker for `gh pr comment --edit-last` / create-or-update flows.
AUCTELIS_COMMENT_MARKER = "<!-- auctelis-authority-diff -->"


def _title(finding: Any) -> str:
    if isinstance(finding, dict):
        return str(finding.get("title") or finding.get("finding_id") or "finding")
    return str(finding.title)


def _sev(finding: Any) -> str:
    if isinstance(finding, dict):
        return str(finding.get("severity") or "")
    return str(finding.severity)


def _unknowns_line(coverage: dict[str, Any]) -> str:
    not_verified = coverage.get("not_verified") or []
    manual = coverage.get("manual_review_families") or []
    unparsed = int(coverage.get("unparsed_agent_config_count") or 0)
    bits: list[str] = []
    if isinstance(not_verified, list) and not_verified:
        labels = []
        for item in not_verified[:2]:
            if isinstance(item, dict):
                labels.append(str(item.get("family") or item.get("surface") or item))
            else:
                labels.append(str(item))
        bits.append("NOT VERIFIED: " + ", ".join(labels))
    if isinstance(manual, list) and manual:
        bits.append("MANUAL_ONLY: " + ", ".join(str(x) for x in manual[:2]))
    if unparsed:
        bits.append(f"NOT PARSED: {unparsed} agent config(s)")
    if not bits:
        return "Unknown: publisher identity, effective permissions, runtime behavior"
    return "Unknown: " + "; ".join(bits)


def _format_owners_for_comment(owners: list[str]) -> str:
    """Render CODEOWNERS as code spans so escape_markdown cannot blank @mentions."""
    bits: list[str] = []
    for raw in owners[:3]:
        name = str(raw or "").strip()
        if not name:
            continue
        if not name.startswith("@"):
            name = f"@{name}"
        # Strip injection-prone chars; keep the login visible inside backticks.
        safe = re.sub(r"[\\`*_{}\[\]()#!|>]", "", name)
        bits.append(f"`{safe}`")
    return ", ".join(bits)


def _required_action(
    verdict: str,
    *,
    growth: bool,
    new_powers: list[Any],
    needs_approval_from: list[str] | None = None,
    comment_only: bool = False,
) -> str:
    owners = [o for o in (needs_approval_from or []) if o]
    if verdict == "BASELINE_NEEDED":
        return "No base lock — seal the baseline with `auctelis lock --update` before relying on growth checks."
    if growth and owners:
        who = _format_owners_for_comment(owners) or "(none)"
        # Owners are already code-spanned; do not re-escape this line.
        return f"Needs approval from: {who}"
    if growth:
        if comment_only:
            # Advisory checks must never imply "no action" on unreviewed growth.
            return "CODEOWNERS review required before merge; this check is advisory."
        return "CODEOWNERS for AUTHORITY.lock (run `auctelis init --owner @team`)"
    if verdict == "NEEDS_REVIEW":
        if new_powers:
            return "Review the new authority, then seal the baseline."
        return "Review the unknown / NOT PARSED entries before merge."
    if verdict == "FAIL_CLOSED":
        return "Fail closed: fix the lock or coverage gap before merge."
    return "No action beyond reviewing Unknowns before merge."


def _sort_findings_by_severity(items: list[Any]) -> list[Any]:
    return sorted(items, key=lambda f: _SEV_RANK.get(_sev(f).upper(), 9))


_ALLOWED_VERDICTS = {
    "PASS",
    "NEEDS_REVIEW",
    "BASELINE_NEEDED",
    "BASELINE_ADOPTED",
    "FAIL_CLOSED",
}


def render_gate_pr_comment(
    report: dict[str, Any],
    *,
    trusted_hosts: set[str] | None = None,
) -> str:
    """PR comment from a tree-truth gate report — no research findings required."""
    coverage = report.get("coverage") if isinstance(report.get("coverage"), dict) else {}
    if not coverage and report.get("unparsed"):
        coverage = {"unparsed_agent_config_count": int(report.get("unparsed") or 0)}
    return render_authority_diff_comment(
        {"findings": [], "coverage": coverage},
        lock_delta=report.get("delta") if isinstance(report.get("delta"), dict) else None,
        needs_approval_from=list(report.get("required_owners") or []) or None,
        verdict=str(report.get("verdict") or "NEEDS_REVIEW"),
        mode=str(report.get("mode") or "") or None,
        baseline_state=str(report.get("baseline_state") or "") or None,
        trusted_hosts=trusted_hosts,
    )


def _is_auctelis_workflow_path(path: str) -> bool:
    """True for ``.github/workflows/auctelis*.yml`` install surfaces (tier 0)."""
    norm = str(path or "").replace("\\", "/").lower()
    if not norm.startswith(".github/workflows/"):
        return False
    name = norm.rsplit("/", 1)[-1]
    return name.startswith("auctelis") and name.endswith((".yml", ".yaml"))


def _first_unpinned_pin_snippet(lock_delta: dict[str, Any] | None) -> str:
    """Pasteable pin snippet for the first unpinned MCP in a lock delta."""
    if not isinstance(lock_delta, dict):
        return ""
    raw_changes = lock_delta.get("changes")
    changes: dict[str, Any] = raw_changes if isinstance(raw_changes, dict) else {}
    candidates: list[dict[str, Any]] = []
    for rec in changes.get("added") or []:
        if isinstance(rec, dict):
            candidates.append(rec)
    for item in changes.get("changed") or []:
        if not isinstance(item, dict):
            continue
        after = item.get("after")
        if isinstance(after, dict):
            candidates.append(after)
    for record in candidates:
        if not is_unpinned_mcp(record):
            continue
        snippet = str(pin_config_snippet(record) or "").strip()
        if snippet:
            return snippet
    return ""


def _delta_record_paths(
    report: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(added_or_changed_records, removed_records)`` from a gate report.

    Live ``diff_authority_locks`` emits ``delta["changes"]``; older callers /
    synthetic tests may still pass ``delta["records"]``.
    """
    raw_delta = report.get("delta")
    delta: dict[str, Any] = raw_delta if isinstance(raw_delta, dict) else {}
    raw_records = delta.get("changes")
    if not isinstance(raw_records, dict):
        raw_records = delta.get("records")
    records: dict[str, Any] = raw_records if isinstance(raw_records, dict) else {}
    added = [r for r in (records.get("added") or []) if isinstance(r, dict)]
    removed = [r for r in (records.get("removed") or []) if isinstance(r, dict)]
    changed_out: list[dict[str, Any]] = []
    for item in records.get("changed") or []:
        if not isinstance(item, dict):
            continue
        after = item.get("after") or item.get("head") or item
        if isinstance(after, dict):
            changed_out.append(after)
    return [*added, *changed_out], removed


def _install_workflow_only(report: dict[str, Any]) -> bool:
    """True when the only authority delta is adding/changing auctelis workflow YAML.

    Initial ``.auctelis.yml`` from ``auctelis init`` (``policy_added``) is allowed;
    edits to an existing policy (``policy_modified`` / ``policy_removed``) are not.
    """
    if bool(report.get("lock_tree_drift")) or int(report.get("unparsed") or 0):
        return False
    raw_delta = report.get("delta")
    delta: dict[str, Any] = raw_delta if isinstance(raw_delta, dict) else {}
    raw_summary = delta.get("summary")
    summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
    if (
        int(summary.get("mcp_tools_added") or 0)
        or int(summary.get("mcp_tools_changed") or 0)
        or bool(summary.get("policy_modified"))
        or bool(summary.get("policy_removed"))
    ):
        return False
    # Allow policy_changed only for the initial `.auctelis.yml` (policy_added).
    # Legacy reports without policy_added reject any policy_changed.
    if bool(summary.get("policy_changed")) and not bool(summary.get("policy_added")):
        return False
    changed, removed = _delta_record_paths(report)
    if removed or not changed:
        return False
    return all(_is_auctelis_workflow_path(str(r.get("path") or "")) for r in changed)


def render_first_run_comment(
    report: dict[str, Any],
    *,
    install_only: bool | None = None,
) -> str:
    """One "watching" comment on the first PR after install.

    Quiet-on-``NONE`` makes a healthy install indistinguishable from a broken
    one, so the Action posts this exactly once when no sticky comment exists
    yet. Clean install PRs that only add ``.github/workflows/auctelis*.yml``
    stay ``PASS``; any other authority growth stays ``NEEDS_REVIEW`` with cards.
    """
    raw_reach = report.get("reach")
    reach: dict[str, Any] = raw_reach if isinstance(raw_reach, dict) else {}
    raw_counts = reach.get("tier_counts")
    counts = raw_counts if isinstance(raw_counts, dict) else {}
    total = int(reach.get("total") or 0)
    tier2 = int(counts.get("tier2") or 0)
    tier1 = int(counts.get("tier1") or 0)
    tier0 = int(counts.get("tier0") or 0)
    verdict = str(report.get("verdict") or "PASS").upper()
    label = str(report.get("label") or "NONE").upper()
    if install_only is None:
        install_only = _install_workflow_only(report)
    watching = (
        verdict == "PASS"
        and label == "NONE"
        and not bool(report.get("meaningful_authority_change"))
        and not bool(report.get("lock_tree_drift"))
        and not int(report.get("unparsed") or 0)
    ) or bool(install_only)
    if watching:
        verdict = "PASS"
        if install_only and label == "GROWTH":
            # Install workflow alone is expected growth — do not alarm.
            label = "NONE"
    else:
        # A first-run file must never present growth as a clean install check.
        verdict = "NEEDS_REVIEW"
    lines = [
        "### auctelis Authority Diff",
        f"**Verdict:** `{verdict}` · label `{label}` · first run",
        f"**Watching:** {total} reach surface(s) — "
        f"{tier2} fail tier · {tier1} comment tier · {tier0} silent",
    ]
    if total == 0:
        lines.append(
            "No agent configuration was discovered in this repository — "
            "run `auctelis check` locally to see what auctelis can see."
        )
    if watching:
        top = [str(card) for card in (reach.get("top_cards") or []) if str(card).strip()][:3]
        if top:
            lines.append("**Top reach:**")
            for card in top:
                lines.append(f"- {escape_markdown(card.lstrip('+-~ '), max_len=180)}")
        lines.append(
            "**Next:** this PR did not change agent authority. The next PR that "
            "adds or changes an MCP server, skill, hook, or permission will show "
            "the Authority Diff."
        )
    else:
        # Surface non-install growth (e.g. smuggled MCP) so the Action cannot
        # hide it by preferring a Watching-only first-run file.
        cards = delta_cards(
            report.get("delta") if isinstance(report.get("delta"), dict) else None,
            limit=5,
            include_overflow_summary=True,
        )
        if not cards:
            cards = [str(card) for card in (reach.get("top_cards") or []) if str(card).strip()][:5]
        if cards:
            lines.append("**Authority delta:**")
            for card in cards:
                lines.append(f"- {escape_markdown(str(card).lstrip('+-~ '), max_len=180)}")
        lines.append("**Next:** authority changed or could not be established — review the diff.")
    return AUCTELIS_COMMENT_MARKER + "\n" + "\n".join(lines) + "\n"


def render_authority_diff_comment(
    findings_doc: dict[str, Any] | None = None,
    *,
    risk_delta: dict[str, Any] | None = None,
    authority_delta: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    lock_delta: dict[str, Any] | None = None,
    policy_mode: str | None = None,
    needs_approval_from: list[str] | None = None,
    verdict: str | None = None,
    mode: str | None = None,
    baseline_state: str | None = None,
    trusted_hosts: set[str] | None = None,
    max_lines: int = 20,
    plain_text: bool = False,
) -> str:
    """Render a short PR body: complete compact reach table (≤5 delta cards).

    Finding IDs and rule IDs stay out of the comment body. The line carries
    name, destination/launcher, env, pin, capabilities, and evidence strength.
    Advisory and enforce comments share this authority section shape.

    ``plain_text`` keeps the same layout for terminal stdout while skipping
    markdown escaping (control sequences are still stripped), so local
    ``diff --base`` output reads ``(no authority change)`` rather than
    ``\\(no authority change\\)``. PR bodies keep the escaped form.
    """
    del authority_snapshot  # reserved
    # policy_mode no longer changes the authority section (lock-only contract).
    del policy_mode

    def _esc(value: str, *, max_len: int = 160) -> str:
        if plain_text:
            return sanitize_terminal_text(value, max_len=max_len)
        return escape_markdown(value, max_len=max_len)

    findings_doc = findings_doc if isinstance(findings_doc, dict) else {}
    findings = list(findings_doc.get("findings") or [])
    coverage = findings_doc.get("coverage") or {}
    summary = (risk_delta or {}).get("summary") if risk_delta else None
    if summary is None and risk_delta and "gated_findings_added" in risk_delta:
        summary = risk_delta

    baseline_norm = str(baseline_state or "").strip().lower()
    baseline_absent = baseline_norm == "absent"
    new_powers: list[Any] = []
    # A real base (committed lock or tree-truth extract) is a baseline even when
    # the delta is empty. Only a failed lockless extract may call this absolute.
    has_baseline = (
        risk_delta is not None or lock_delta is not None or baseline_norm in {"present", "tree"}
    )
    if baseline_absent:
        has_baseline = False
    if risk_delta:
        changes = risk_delta.get("changes") or {}
        for key in ("high_or_critical_new_findings", "gated_new_findings"):
            items = changes.get(key)
            if isinstance(items, list) and items:
                new_powers = [f for f in items if isinstance(f, dict) and is_gate_finding(f)]
                break
    elif not has_baseline:
        new_powers = [f for f in findings if is_gate_finding(f)]
    new_powers = _sort_findings_by_severity(new_powers)

    component_lines: list[str] = []
    delta_doc = authority_delta or (risk_delta or {}).get("authority_delta")
    if isinstance(delta_doc, dict):
        component_lines = render_component_delta_lines(delta_doc)
    elif isinstance(risk_delta, dict) and risk_delta.get("component_delta_lines"):
        component_lines = list(risk_delta.get("component_delta_lines") or [])

    lock_summary = dict((lock_delta or {}).get("summary") or {})
    label = delta_label(lock_summary)
    if baseline_absent:
        # Absolute head reach is not a delta label (no GROWTH vs a base).
        label = "NONE"
    growth = label == "GROWTH"
    if verdict is None:
        # Unreviewed growth is never PASS, even when CODEOWNERS owners exist —
        # GitHub enforces the review; this comment must not pre-approve it.
        verdict = "NEEDS_REVIEW" if growth or new_powers else "PASS"
    verdict = str(verdict).upper()
    if verdict not in _ALLOWED_VERDICTS:
        verdict = "NEEDS_REVIEW"
    # An unparsed agent config means authority could not be established; never
    # emit PASS in that case.
    try:
        unparsed_count = int(coverage.get("unparsed_agent_config_count") or 0)
    except (TypeError, ValueError):
        unparsed_count = 0
    if unparsed_count and verdict == "PASS":
        verdict = "NEEDS_REVIEW"

    mode_bit = ""
    mode_norm = str(mode or "").strip().lower()
    if mode_norm in {"comment-only", "comment_only", "advisory"}:
        mode_bit = " · mode `comment-only`"
    elif mode_norm in {"enforce", "locked"}:
        mode_bit = " · mode `enforce`"

    # Marker is sticky-comment metadata — not counted toward the ≤12 visible lines.
    visible: list[str] = [
        "### auctelis Authority Diff",
        f"**Verdict:** `{verdict}` · label `{label}`{mode_bit}",
    ]

    changed_bits: list[str] = []
    for key in ("additions", "expansions", "reductions", "replacements"):
        count = int(lock_summary.get(key) or 0)
        if count:
            changed_bits.append(f"{key} {count}")
    if lock_summary.get("policy_changed"):
        changed_bits.append("policy")
    if summary is not None:
        gated = int(summary.get("gated_findings_added") or 0)
        if gated:
            changed_bits.append(f"gated findings {gated}")
    if not changed_bits and component_lines:
        changed_bits.append(f"component deltas {len(component_lines)}")
    if not changed_bits:
        if baseline_absent:
            changed_bits.append("absolute head reach (no base lock)")
        else:
            changed_bits.append(
                "no new authority vs baseline" if has_baseline else "absolute head reach"
            )
    visible.append("**Changed:** " + _esc(", ".join(changed_bits), max_len=140))
    if baseline_absent:
        visible.append(
            "**Baseline:** none at the base ref — showing absolute head reach. "
            "Seal with `auctelis lock --update`."
        )

    visible.append("**Authority delta:**")
    cards = delta_cards(
        lock_delta,
        limit=5,
        include_overflow_summary=True,
        trusted_hosts=trusted_hosts,
    )
    if not cards and isinstance(lock_delta, dict):
        cards = [
            f"- {line.lstrip('+-~ ')}"
            for line in (lock_delta.get("lines") or [])
            if " representation " not in f" {line} "
        ][:5]
    if not cards and component_lines:
        cards = [f"- {line.lstrip('+-~ ')}" for line in component_lines[:5]]
    if not cards and new_powers:
        cards = [
            f"- {_esc(_sev(finding), max_len=12)} {_esc(_title(finding), max_len=120)}"
            for finding in new_powers[:5]
        ]
    if not cards:
        unparsed = int((findings_doc.get("coverage") or {}).get("unparsed_agent_config_count") or 0)
        cards = ["- NOT PARSED (coverage gap)" if unparsed else "- (no authority change)"]
    for card in cards:
        visible.append(f"- {_esc(card.lstrip('+-~ '), max_len=180)}")

    # AUCT-040: one pasteable pin fix. Markdown renders a code span with no
    # backslash or entity escaping. A newline or over-budget snippet is omitted
    # rather than truncated. Plain text keeps the previous one-line sanitizer.
    pin_snippet = _first_unpinned_pin_snippet(lock_delta)
    if pin_snippet and len(visible) < max_lines:
        if plain_text:
            safe = sanitize_terminal_text(pin_snippet, max_len=100)
            pin_line = f"**Pin fix:** `{safe}` (pinning turns this into PASS / REDUCTION)"
            if len(pin_line) > 160:
                pin_line = pin_line[:159] + "…"
            visible.append(pin_line)
        else:
            span = markdown_code_span(pin_snippet)
            if span is not None:
                visible.append(f"**Pin fix:** {span} (pinning turns this into PASS / REDUCTION)")

    visible.append(_esc(_unknowns_line(coverage), max_len=200))

    required = _required_action(
        verdict,
        growth=growth,
        new_powers=new_powers,
        needs_approval_from=needs_approval_from if growth else None,
        comment_only=mode_norm in {"comment-only", "comment_only", "advisory"},
    )
    # Owner names are already code-spanned; static instruction text stays readable.
    visible.append(required if len(required) <= 160 else required[:159] + "…")

    suppressed_n = int(findings_doc.get("suppression_count") or 0)
    if not suppressed_n:
        suppressed_n = sum(1 for f in findings if isinstance(f, dict) and f.get("suppressed"))
    if suppressed_n and len(visible) < max_lines:
        visible.append(f"Suppressions retained: {suppressed_n}")

    while len(visible) > max_lines and len(visible) > 6:
        # Drop middle detail first; keep header, verdict, authority, footer action.
        if len(visible) - 2 > 4:
            visible.pop(4)
        else:
            break
    return AUCTELIS_COMMENT_MARKER + "\n" + "\n".join(visible) + "\n"
