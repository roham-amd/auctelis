"""Single source of truth for which findings may block CI / annotate PRs.

Capability observations are inventory — they never gate by default.
``NAME_MARKER`` evidence never gates (weak naming signal only).
``require_review`` classes can fail the gate independent of severity.
"""

from __future__ import annotations

from typing import Any, Protocol

from authdiff.security.finding_fields import (
    evidence_ids,
    evidence_strength,
    finding_class,
    finding_severity,
    is_suppressed,
)
from authdiff.security.review_classes import require_review_hits

GATE_FINDING_CLASSES: frozenset[str] = frozenset({"SECURITY_FINDING", "EXPOSURE"})
HIGH_SEVERITIES: frozenset[str] = frozenset({"CRITICAL", "HIGH"})


class _GateFinding(Protocol):
    # Properties keep Literal severity/class fields structural-subtype compatible.
    @property
    def finding_class(self) -> str: ...

    @property
    def severity(self) -> str: ...


def is_gate_finding(finding: _GateFinding | dict[str, Any]) -> bool:
    """True when the finding may participate in fail-on / annotations."""
    if is_suppressed(finding):
        return False
    # NAME_MARKER is triage-only — never severity-gate or require_review alone.
    if evidence_strength(finding) == "NAME_MARKER":
        return False
    # Gated findings must cite reproducible evidence (100% evidence-ref target).
    if not evidence_ids(finding):
        return False
    return finding_class(finding) in GATE_FINDING_CLASSES


def is_high_gate_finding(finding: _GateFinding | dict[str, Any]) -> bool:
    """True for CRITICAL/HIGH gate findings (``fail_on=high``)."""
    if not is_gate_finding(finding):
        return False
    return finding_severity(finding) in HIGH_SEVERITIES


def gated_findings(findings: list[Any]) -> list[Any]:
    return [f for f in findings if is_gate_finding(f)]


def high_gate_findings(findings: list[Any]) -> list[Any]:
    return [f for f in findings if is_high_gate_finding(f)]


def compute_exit_code(
    fail_on: str | None,
    *,
    findings: list[Any],
    risk_delta_summary: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    parser_events: list[dict[str, Any]] | None = None,
    require_review: list[str] | None = None,
) -> int:
    """Compute process exit code for ``fail_on`` / ``require_review`` policy.

    When a baseline risk delta is present, gate on **new** gated findings only
    (no fall-through to legacy absolute head findings). Without a baseline,
    absolute head gated findings apply.

    ``require_review`` classes fail closed whenever listed and matched, even if
    ``fail_on`` is ``never`` — listing a class *is* the gate for that authority.

    Unparsed / oversize agent configs fail closed whenever ``fail_on`` is set —
    matching ``compute_decision`` REVIEW semantics (never exit 0 on gaps).
    """
    if require_review_hits(findings, require_review):
        return 1
    if fail_on not in {"high", "any"}:
        return 0
    # Local import avoids a circular dependency (decision → gating).
    from authdiff.security.decision import unparsed_agent_config_count

    if unparsed_agent_config_count(coverage, parser_events) > 0:
        return 1
    if risk_delta_summary is not None:
        if fail_on == "high":
            return 1 if risk_delta_summary.get("high_or_critical_findings_added") else 0
        # fail_on == "any"
        return 1 if risk_delta_summary.get("gated_findings_added") else 0
    if fail_on == "high" and high_gate_findings(findings):
        return 1
    if fail_on == "any" and gated_findings(findings):
        return 1
    return 0
