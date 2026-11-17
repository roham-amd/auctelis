"""Compact Authority Diff PR comment (≤12 lines).

One verdict, at most five risk-ranked authority cards, the unknowns (including
``NOT PARSED``), and the required action. Finding IDs and rule IDs stay in the
artifacts, not the review UI. Target-derived strings are escaped so findings
cannot inject markdown links/mentions.
"""

from __future__ import annotations

import re
from typing import Any

from auctelis.authority_card import delta_cards
from auctelis.authority_lock import delta_label
from auctelis.security.authority import render_component_delta_lines
from auctelis.security.gating import is_gate_finding
from auctelis.textutil import escape_markdown

__all__ = [
    "AUCTELIS_COMMENT_MARKER",
    "escape_markdown",
    "render_authority_diff_comment",
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
) -> str:
    """Render a short PR body: complete compact reach table (≤5 delta cards).

    Finding IDs and rule IDs stay out of the comment body. The line carries
    name, destination/launcher, env, pin, capabilities, and evidence strength.
    Advisory and enforce comments share this authority section shape.
    """
    del authority_snapshot  # reserved
    # policy_mode no longer changes the authority section (lock-only contract).
    del policy_mode
    findings_doc = findings_doc if isinstance(findings_doc, dict) else {}
    findings = list(findings_doc.get("findings") or [])
    coverage = findings_doc.get("coverage") or {}
    summary = (risk_delta or {}).get("summary") if risk_delta else None
    if summary is None and risk_delta and "gated_findings_added" in risk_delta:
        summary = risk_delta

    baseline_absent = str(baseline_state or "").strip().lower() == "absent"
    new_powers: list[Any] = []
    # A real base lock is a baseline even when the delta is empty. Only a
    # truly lockless ref may call this an absolute head scan.
    has_baseline = (
        risk_delta is not None
        or lock_delta is not None
        or str(baseline_state or "").strip().lower() == "present"
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
    visible.append("**Changed:** " + escape_markdown(", ".join(changed_bits), max_len=140))
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
            f"- {escape_markdown(_sev(finding), max_len=12)} "
            f"{escape_markdown(_title(finding), max_len=120)}"
            for finding in new_powers[:5]
        ]
    if not cards:
        unparsed = int((findings_doc.get("coverage") or {}).get("unparsed_agent_config_count") or 0)
        cards = ["- NOT PARSED (coverage gap)" if unparsed else "- (no authority change)"]
    for card in cards:
        visible.append(f"- {escape_markdown(card.lstrip('+-~ '), max_len=180)}")

    visible.append(escape_markdown(_unknowns_line(coverage), max_len=200))

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
