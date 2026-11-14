"""Compact Authority Diff PR comment (≤12 lines).

One verdict, at most three old → new authority cards, the unknowns (including
``NOT PARSED``), and the required action. Finding IDs and rule IDs stay in the
artifacts, not the review UI. Target-derived strings are escaped so findings
cannot inject markdown links/mentions.
"""

from __future__ import annotations

import re
from typing import Any

from auctelis.authority_card import count_cards, delta_cards
from auctelis.authority_lock import delta_label
from auctelis.security.authority import render_component_delta_lines
from auctelis.security.gating import is_gate_finding
from auctelis.textutil import escape_markdown

__all__ = [
    "AUCTELIS_COMMENT_MARKER",
    "escape_markdown",
    "render_authority_diff_comment",
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
) -> str:
    owners = [o for o in (needs_approval_from or []) if o]
    if growth and owners:
        who = _format_owners_for_comment(owners) or "(none)"
        # Owners are already code-spanned; do not re-escape this line.
        return f"Needs approval from: {who}"
    if verdict == "NEEDS_REVIEW":
        if growth:
            return "CODEOWNERS for AUTHORITY.lock (run `auctelis ci init --owner @team`)"
        if new_powers:
            return "Review the new authority, then seal the baseline."
        return "Review the unknown / NOT PARSED entries before merge."
    if verdict == "FAIL_CLOSED":
        return "Fail closed: fix the lock or coverage gap before merge."
    return "No action beyond reviewing Unknowns before merge."


def _sort_findings_by_severity(items: list[Any]) -> list[Any]:
    return sorted(items, key=lambda f: _SEV_RANK.get(_sev(f).upper(), 9))


_ALLOWED_VERDICTS = {"PASS", "NEEDS_REVIEW", "BASELINE_ADOPTED", "FAIL_CLOSED"}


def render_authority_diff_comment(
    findings_doc: dict[str, Any],
    *,
    risk_delta: dict[str, Any] | None = None,
    authority_delta: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    lock_delta: dict[str, Any] | None = None,
    policy_mode: str | None = None,
    needs_approval_from: list[str] | None = None,
    verdict: str | None = None,
    max_lines: int = 12,
) -> str:
    """Render a short PR body: one verdict, at most three old → new lines.

    Finding IDs and rule IDs stay out of the comment body. The line carries
    name, destination/launcher, capabilities, and evidence strength only.
    """
    del authority_snapshot, policy_mode  # reserved / not part of the public dialect
    findings = list(findings_doc.get("findings") or [])
    coverage = findings_doc.get("coverage") or {}
    summary = (risk_delta or {}).get("summary") if risk_delta else None
    if summary is None and risk_delta and "gated_findings_added" in risk_delta:
        summary = risk_delta

    new_powers: list[Any] = []
    has_baseline = risk_delta is not None
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
    growth = label == "GROWTH"
    if verdict is None:
        if growth and not needs_approval_from:
            verdict = "NEEDS_REVIEW"
        elif growth:
            verdict = "PASS"
        elif new_powers:
            verdict = "NEEDS_REVIEW"
        else:
            verdict = "PASS"
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

    # Marker is sticky-comment metadata — not counted toward the ≤12 visible lines.
    visible: list[str] = [
        "### auctelis Authority Diff",
        f"**Verdict:** `{verdict}` · label `{label}`",
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
        changed_bits.append(
            "no new authority vs baseline" if has_baseline else "absolute head scan"
        )
    visible.append("**Changed:** " + escape_markdown(", ".join(changed_bits), max_len=140))

    visible.append("**Authority delta:**")
    cards = delta_cards(lock_delta, limit=3)
    if not cards and isinstance(lock_delta, dict):
        cards = [
            f"- {line.lstrip('+-~ ')}"
            for line in (lock_delta.get("lines") or [])
            if " representation " not in f" {line} "
        ][:3]
    if not cards and component_lines:
        cards = [f"- {line.lstrip('+-~ ')}" for line in component_lines[:3]]
    if not cards and new_powers:
        cards = [
            f"- {escape_markdown(_sev(finding), max_len=12)} "
            f"{escape_markdown(_title(finding), max_len=120)}"
            for finding in new_powers[:3]
        ]
    if not cards:
        unparsed = int((findings_doc.get("coverage") or {}).get("unparsed_agent_config_count") or 0)
        cards = ["- NOT PARSED (coverage gap)" if unparsed else "- (no authority change)"]
    for card in cards:
        visible.append(f"- {escape_markdown(card.lstrip('+-~ '), max_len=180)}")
    total_cards = count_cards(lock_delta)
    if total_cards > len(cards):
        visible.append(f"- +{total_cards - len(cards)} more")

    visible.append(escape_markdown(_unknowns_line(coverage), max_len=200))

    required = _required_action(
        verdict,
        growth=growth,
        new_powers=new_powers,
        needs_approval_from=needs_approval_from if growth else None,
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
