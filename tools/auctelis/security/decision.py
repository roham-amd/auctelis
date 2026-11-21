"""Gate decision labels for reports, PR comments, and agent digests.

Decisions are derived from gated findings + coverage honesty — never a trust score.
"""

from __future__ import annotations

from typing import Any, Literal

from auctelis.inventory.coverage import (
    count_unparsed_agent_configs,
    unparsed_agent_config_count_from_coverage,
)
from auctelis.security.finding_fields import finding_class, finding_severity
from auctelis.security.gating import HIGH_SEVERITIES, is_gate_finding, is_high_gate_finding

# Legacy alias kept for one release so old fixtures/docs still parse.
Decision = Literal[
    "BLOCK",
    "REVIEW",
    "NO-GATED-FINDINGS",
]

# Distinct from Decision: whether authority itself was established.
AuthorityEstablishment = Literal[
    "NO_NEW_AUTHORITY",
    "AUTHORITY_EXPANDED",
    "AUTHORITY_NOT_ESTABLISHED",
]


def unparsed_agent_config_count(
    coverage: dict[str, Any] | None = None,
    parser_events: list[dict[str, Any]] | None = None,
) -> int:
    """Count agent-config parse/skip events that must fail closed.

    Delegates to the single coverage implementation so the gate, check, and
    research decision layer cannot disagree about which files count.
    """
    cov = coverage or {}
    if parser_events:
        return count_unparsed_agent_configs(parser_events)
    return unparsed_agent_config_count_from_coverage(cov)


def authority_establishment(
    *,
    coverage: dict[str, Any] | None = None,
    risk_delta: dict[str, Any] | None = None,
    lock_delta: dict[str, Any] | None = None,
    decision: Decision | None = None,
) -> AuthorityEstablishment:
    """Distinguish *no new authority* from *authority could not be established*.

    A clean decision with sparse SUPPORTED coverage is not the same as proving
    that no authority changed — adapters may simply not have established it.
    """
    cov = coverage or {}
    maturity = cov.get("component_counts_by_maturity") or {}
    if not isinstance(maturity, dict):
        maturity = {}
    supported = int(maturity.get("SUPPORTED") or 0)
    partial = int(maturity.get("PARTIAL") or 0)
    manual = int(maturity.get("MANUAL_ONLY") or 0)
    unsupported = int(maturity.get("UNSUPPORTED") or 0)
    total = supported + partial + manual + unsupported
    unparsed = unparsed_agent_config_count(cov)
    lock_summary = (lock_delta or {}).get("summary") if isinstance(lock_delta, dict) else None
    expanded = False
    if isinstance(lock_summary, dict):
        expanded = bool(
            int(lock_summary.get("additions") or 0)
            or int(lock_summary.get("expansions") or 0)
            or int(lock_summary.get("replacements") or 0)
            or lock_summary.get("meaningful_authority_change")
        )
    if risk_delta is not None and int(risk_delta.get("gated_findings_added") or 0) > 0:
        expanded = True
    if decision in {"BLOCK", "REVIEW"} and expanded:
        return "AUTHORITY_EXPANDED"
    if expanded:
        return "AUTHORITY_EXPANDED"
    # Significant unknown surface → cannot claim "no new authority".
    if (
        unparsed > 0
        or (total > 0 and supported * 2 < total)
        or (total == 0 and partial + manual > 0)
    ):
        return "AUTHORITY_NOT_ESTABLISHED"
    return "NO_NEW_AUTHORITY"


def compute_decision(
    findings: list[Any],
    *,
    coverage: dict[str, Any] | None = None,
    risk_delta: dict[str, Any] | None = None,
    parser_events: list[dict[str, Any]] | None = None,
    require_review: list[str] | None = None,
) -> Decision:
    """Return the operator-facing decision for a scan or risk delta.

    When ``risk_delta`` is provided (baseline mode), gate on **new** authority
    only — never fall through to legacy absolute head findings.
    """
    from auctelis.security.review_classes import require_review_hits

    if require_review_hits(findings, require_review):
        return "REVIEW"

    if risk_delta is not None:
        if risk_delta.get("high_or_critical_findings_added"):
            return "BLOCK"
        if risk_delta.get("gated_findings_added"):
            return "REVIEW"
        # Unparsed configs still fail closed even when the finding delta is empty.
        if unparsed_agent_config_count(coverage, parser_events) > 0:
            return "REVIEW"
        return "NO-GATED-FINDINGS"

    gated = [f for f in findings if is_gate_finding(f)]
    if any(is_high_gate_finding(f) for f in gated):
        return "BLOCK"
    if gated:
        return "REVIEW"

    # Unparsed / oversize agent configs fail closed as REVIEW — never a quiet pass.
    if unparsed_agent_config_count(coverage, parser_events) > 0:
        return "REVIEW"

    # Never emit a bare PASS — incomplete coverage is the honest default.
    return "NO-GATED-FINDINGS"


def decision_sentences(
    decision: Decision,
    findings: list[Any],
    *,
    risk_delta: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
) -> list[str]:
    """Three short sentences explaining the decision (report lead)."""
    gated = [f for f in findings if is_gate_finding(f)]
    high = [f for f in gated if finding_severity(f) in HIGH_SEVERITIES]
    added = int((risk_delta or {}).get("gated_findings_added") or 0)
    unparsed = unparsed_agent_config_count(coverage)
    cov_line = coverage_score_line(coverage)
    label = decision

    if label == "BLOCK":
        lead = (
            f"BLOCK: {len(high)} high/critical authority issue(s) require a fix or "
            "explicit risk acceptance before merge/install."
        )
    elif label == "REVIEW":
        if unparsed and not gated:
            lead = (
                f"REVIEW: {unparsed} agent-config file(s) were unparsed or oversize "
                "(fail closed — not a clearance)."
            )
        else:
            lead = (
                f"REVIEW: {len(gated)} gated finding(s) need human judgment "
                "(not automatically merge-blocking at fail-on=high)."
            )
    else:
        lead = (
            f"NO-GATED-FINDINGS ({cov_line.split(';')[0].replace('Coverage: ', 'coverage ')}): "
            "no gated SECURITY_FINDING/EXPOSURE fired; this is not a security clearance."
        )

    if risk_delta is not None:
        delta = (
            f"Authority diff vs baseline: {added} new gated finding(s), "
            f"{int(risk_delta.get('high_or_critical_findings_added') or 0)} high/critical."
        )
    else:
        delta = (
            f"Observed {len(gated)} gated finding(s) and "
            f"{sum(1 for f in findings if finding_class(f) == 'CAPABILITY')} capability observation(s)."
        )

    if risk_delta is not None and label == "NO-GATED-FINDINGS":
        establishment = authority_establishment(
            coverage=coverage, risk_delta=risk_delta, decision=label
        )
        if establishment == "AUTHORITY_NOT_ESTABLISHED":
            lead = (
                "NO-GATED-FINDINGS: no *new* gated findings vs baseline, but authority "
                "could not be fully established in the supported subset — not a clearance."
            )
        else:
            lead = (
                "NO-GATED-FINDINGS: no *new* gated authority vs baseline "
                "(legacy findings do not block in diff mode)."
            )
    elif label == "NO-GATED-FINDINGS":
        establishment = authority_establishment(coverage=coverage, decision=label)
        if establishment == "AUTHORITY_NOT_ESTABLISHED":
            lead = (
                "NO-GATED-FINDINGS in the supported subset; authority could not be "
                "fully established — review coverage gaps before treating this as clean."
            )
    action = (
        "Next: `auctelis check` / `auctelis why <name>` for the lock delta; "
        "`auctelis-dev scan --full` for research annotations (not a gate input)."
    )
    return [lead, delta, action]


def coverage_score_line(coverage: dict[str, Any] | None) -> str:
    """One-line coverage honesty for reports (not a trust score)."""
    cov = coverage or {}
    maturity = cov.get("component_counts_by_maturity") or {}
    if not isinstance(maturity, dict):
        maturity = {}
    supported = int(maturity.get("SUPPORTED") or 0)
    partial = int(maturity.get("PARTIAL") or 0)
    manual = int(maturity.get("MANUAL_ONLY") or 0)
    total = supported + partial + manual + int(maturity.get("UNSUPPORTED") or 0)
    unparsed = int(cov.get("unparsed_agent_config_count") or 0)
    if total == 0 and unparsed == 0:
        return "Coverage: no adapter-classified components (treat as gap, not safety)."
    pct = round(100 * supported / total) if total else 0
    base = (
        f"Coverage: {pct}% SUPPORTED ({supported}/{total}); PARTIAL={partial} MANUAL_ONLY={manual}"
    )
    if unparsed:
        base += f"; UNPARSED={unparsed}"
    return base + " — clean result ≠ safe."
