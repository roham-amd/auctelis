"""Human-readable terminal and markdown reports for auctelis scans."""

from __future__ import annotations

from typing import Any

from auctelis.security.decision import (
    compute_decision,
    coverage_score_line,
    decision_sentences,
)
from auctelis.security.engine import ScanResult
from auctelis.security.gating import HIGH_SEVERITIES, is_gate_finding, is_high_gate_finding
from auctelis.security.models import Finding


def _evidence_path(scan: ScanResult, finding: Finding) -> str:
    if not finding.evidence_ids:
        return ""
    for ev in scan.evidences:
        if ev.evidence_id == finding.evidence_ids[0]:
            parts = [ev.file_path or ""]
            if ev.line_start:
                span = str(ev.line_start)
                if ev.line_end and ev.line_end != ev.line_start:
                    span = f"{ev.line_start}-{ev.line_end}"
                parts.append(f":{span}")
            return "".join(parts)
    return ""


def _ordered_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (
            {"SECURITY_FINDING": 0, "EXPOSURE": 1, "CAPABILITY": 2}.get(f.finding_class, 9),
            {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}.get(
                f.severity, 9
            ),
        ),
    )


def _authority_surfaces(scan: ScanResult, ordered: list[Finding]) -> list[str]:
    """Top authority-bearing findings as decision-oriented surface cards."""
    lines: list[str] = []
    surfaces = [f for f in ordered if is_gate_finding(f)][:5]
    if not surfaces:
        return [
            "",
            "AUTHORITY SURFACES",
            "  No high-priority SECURITY_FINDING or EXPOSURE observations.",
            "  Capability inventory may still require human review.",
        ]
    lines.extend(["", "AUTHORITY SURFACES (review required)"])
    for finding in surfaces:
        path = _evidence_path(scan, finding)
        lines.append(f"  [{finding.severity}] {finding.finding_id}  {finding.title}")
        lines.append(f"      class: {finding.finding_class}  confidence: {finding.confidence}")
        if path:
            lines.append(f"      evidence: {path}")
        lines.append(f"      action: {finding.recommended_action}")
    return lines


def _authority_path_example(scan: ScanResult, ordered: list[Finding]) -> list[str]:
    """First high-value finding rendered as a short authority path."""
    candidates = [
        f for f in ordered if is_gate_finding(f) and f.severity in (*HIGH_SEVERITIES, "MEDIUM")
    ]
    if not candidates:
        candidates = list(ordered[:1])
    if not candidates:
        return []
    finding = candidates[0]
    path = _evidence_path(scan, finding)
    return [
        "",
        "EXAMPLE AUTHORITY PATH",
        f"  {finding.entry_point or path or finding.title}",
        f"  → {finding.trust_boundary or 'trust boundary not established'}",
        f"  → {finding.impact or 'impact not established'}",
        f"  [{finding.finding_class}] {finding.finding_id}: {finding.title}",
        f"  Next: {finding.recommended_action}",
    ]


def _adapter_maturity_lines(scan: ScanResult) -> list[str]:
    matrix = scan.coverage.get("adapter_matrix") or []
    if not matrix:
        return []
    lines = ["", "ADAPTER COVERAGE"]
    for row in matrix:
        family = row.get("family") or "?"
        maturity = row.get("maturity") or "?"
        adapter = row.get("adapter") or "—"
        lines.append(f"  {str(family).ljust(28)} {str(maturity).ljust(12)} {adapter}")
    return lines


def render_terminal_report(
    scan: ScanResult,
    *,
    risk_delta: dict[str, Any] | None = None,
    full: bool = False,
) -> str:
    """Default is ≤15 lines; pass ``full=True`` for the legacy long report."""
    if not full:
        return render_short_terminal_report(scan, risk_delta=risk_delta)
    return render_full_terminal_report(scan, risk_delta=risk_delta)


def render_short_terminal_report(
    scan: ScanResult,
    *,
    risk_delta: dict[str, Any] | None = None,
) -> str:
    """Compact first-run output (JTBD: what can agents do / what changed)."""
    ordered = _ordered_findings(scan.findings)
    decision = compute_decision(scan.findings, coverage=scan.coverage, risk_delta=risk_delta)
    lead = decision_sentences(decision, scan.findings, risk_delta=risk_delta)
    comps = scan.inventory.get("components") or []
    mcp_n = sum(
        1 for c in comps if isinstance(c, dict) and c.get("type") == "MCP Server Registration"
    )
    hook_n = sum(1 for c in comps if isinstance(c, dict) and c.get("type") == "Hook")
    skill_n = sum(1 for c in comps if isinstance(c, dict) and c.get("type") == "Skill")
    gated = [f for f in ordered if is_gate_finding(f)]
    lines = [
        f"auctelis {scan.product_version} — {mcp_n} MCP, {hook_n} hooks, {skill_n} skills",
        f"ANNOTATION DECISION: {decision} (not a gate; use auctelis gate)",
        lead[0],
        coverage_score_line(scan.coverage),
    ]
    for finding in gated[:3]:
        path = _evidence_path(scan, finding) or finding.entry_point or ""
        lines.append(
            f"  [{finding.severity}] {finding.rule_id}: {finding.title}"
            + (f" ({path})" if path else "")
        )
    if len(gated) > 3:
        lines.append(f"  … +{len(gated) - 3} more gated (auctelis scan --full)")
    lines.append("Next: auctelis watch | auctelis explain F-00N | auctelis scan --full")
    return "\n".join(lines)


def render_full_terminal_report(
    scan: ScanResult,
    *,
    risk_delta: dict[str, Any] | None = None,
) -> str:
    counts = scan.inventory.get("coverage", {}).get("component_counts_by_type") or {}
    sev = scan.findings_by_severity()
    by_class = scan.findings_by_class()
    ordered = _ordered_findings(scan.findings)
    high_priority = sum(
        1 for f in scan.findings if f.severity in HIGH_SEVERITIES and is_gate_finding(f)
    )
    unverified = len(scan.coverage.get("not_verified") or [])
    decision = compute_decision(scan.findings, coverage=scan.coverage, risk_delta=risk_delta)
    lead = decision_sentences(decision, scan.findings, risk_delta=risk_delta)
    # Public verdict language is the lock/gate vocabulary. Scanner severities
    # annotate; they are not a second BLOCK gate. Map for the short summary.
    gate_vocab = {
        "BLOCK": "GROWTH",
        "REVIEW": "NEEDS_REVIEW",
        "NO-GATED-FINDINGS": "PASS",
    }.get(decision, decision)
    lines = [
        "auctelis — Authority Diff for AI agents",
        f"Product: auctelis {scan.product_version}  (tooling {scan.package_version})",
        f"Repository: {scan.repository_path}",
        f"Commit: {scan.commit or 'unknown'}",
        "",
        f"Authority delta: {gate_vocab}",
        f"  (annotations only — enforce with `auctelis gate`; legacy DECISION: {decision})",
        f"  {lead[0]}",
        f"  {lead[1]}",
        f"  {lead[2]}",
        f"  {coverage_score_line(scan.coverage)}",
        "",
        "ANNOTATION SUMMARY",
        f"  Components discovered              {len(scan.inventory.get('components') or [])}",
        f"  Authority-bearing components       {scan.authority_bearing_count}",
        f"  External connections               {scan.external_destination_count}",
        f"  High-priority review items         {high_priority}",
        f"  Unverified control surfaces        {unverified}",
        "",
        "OBSERVATION CLASSES",
        f"  Security findings                  {by_class.get('SECURITY_FINDING', 0)}",
        f"  Exposure observations              {by_class.get('EXPOSURE', 0)}",
        f"  Capability observations            {by_class.get('CAPABILITY', 0)}",
    ]
    lines.extend(_authority_surfaces(scan, ordered))
    lines.extend(_authority_path_example(scan, ordered))

    lines.extend(
        [
            "",
            "COMPONENTS BY TYPE",
        ]
    )
    if counts:
        width = max(len(str(k)) for k in counts) + 2
        for name, count in sorted(counts.items()):
            lines.append(f"  {str(name).ljust(width)}{count}")
    else:
        lines.append("  (none discovered by deterministic adapters)")

    lines.extend(
        [
            "",
            "ALL FINDINGS",
            f"  CRITICAL {sev.get('CRITICAL', 0)}  HIGH {sev.get('HIGH', 0)}  "
            f"MEDIUM {sev.get('MEDIUM', 0)}  LOW {sev.get('LOW', 0)}  "
            f"INFO {sev.get('INFORMATIONAL', 0)}",
        ]
    )
    if not scan.findings:
        lines.append("  No deterministic rule findings. This is NOT a clean bill of health.")
    else:
        for finding in ordered[:12]:
            lines.append(
                f"  [{finding.finding_class}/{finding.severity}/{finding.confidence}] "
                f"{finding.finding_id} {finding.title}"
            )
            path = _evidence_path(scan, finding)
            if path:
                lines.append(f"      evidence: {path}")
            lines.append(f"      action: {finding.recommended_action}")

    coverage = scan.coverage
    lines.extend(
        [
            "",
            "COVERAGE",
            f"  Deterministically discovered  {coverage.get('deterministically_discovered', 0)}",
            f"  Adapter maturity              {coverage.get('component_counts_by_maturity')}",
        ]
    )
    lines.extend(_adapter_maturity_lines(scan))
    lines.extend(
        [
            "",
            "NOT VERIFIED",
        ]
    )
    for item in coverage.get("not_verified") or ["(see inventory coverage)"]:
        lines.append(f"  - {item}")
    manual = coverage.get("manual_review_families") or []
    if manual:
        lines.append("  Manual-only / unsupported families:")
        for family in manual:
            lines.append(f"    - {family}")

    lines.extend(
        [
            "",
            "RESIDUAL RISK / NEXT ACTIONS",
            "  1. Review AUTHORITY SURFACES above before install/merge/deploy.",
            "  2. `auctelis lock` then protect AUTHORITY.lock with CODEOWNERS.",
            "  3. `auctelis explain F-00N` for evidence, attack path, and remediation.",
            "  4. Optional AI deep review: skills/auctelis-auditor (consumes this evidence).",
            "",
            "IMPORTANT",
            "  Capability ≠ vulnerability. Exposure ≠ confirmed exploit.",
            "  Incomplete coverage never equals safety.",
            "  Observed / Potential / Not verified remain distinct from Verified impact.",
            "",
        ]
    )
    return "\n".join(lines)


def render_finding_explanation(scan: ScanResult, finding: Finding) -> str:
    evidence_lines: list[str] = []
    for eid in finding.evidence_ids:
        for ev in scan.evidences:
            if ev.evidence_id == eid:
                loc = ev.file_path or "(no path)"
                if ev.line_start:
                    loc = f"{loc}:{ev.line_start}"
                    if ev.line_end and ev.line_end != ev.line_start:
                        loc = f"{loc}-{ev.line_end}"
                digest = f" digest={ev.content_digest}" if ev.content_digest else ""
                commit = f" commit={ev.source_commit}" if ev.source_commit else ""
                evidence_lines.append(
                    f"- `{ev.evidence_id}` [{ev.evidence_class}/{ev.verification_status}] "
                    f"{loc}{digest}{commit}: {ev.summary}"
                )
                for lim in ev.limitations:
                    evidence_lines.append(f"  limitation: {lim}")
    lines = [
        f"# {finding.finding_id}: {finding.title}",
        "",
        f"- Rule: `{finding.rule_id}`",
        f"- Class: **{finding.finding_class}** "
        f"(CAPABILITY = what it can do; EXPOSURE = reachability; "
        f"SECURITY_FINDING = evidenced security concern)",
        f"- Severity: **{finding.severity}**",
        f"- Confidence: **{finding.confidence}**",
        f"- Exposure: {finding.exposure}",
        f"- Components: {', '.join(finding.component_ids) or '(none)'}",
        f"- Capabilities: {', '.join(finding.capabilities) or '(none)'}",
        "",
        "## What was observed",
        "",
        finding.description,
        "",
        "## Attack path reasoning",
        "",
        f"1. Attacker control: {finding.attacker_control or 'NOT VERIFIED'}",
        f"2. Entry point: {finding.entry_point or 'NOT VERIFIED'}",
        f"3. Trust boundary: {finding.trust_boundary or 'NOT VERIFIED'}",
        f"4. Impact: {finding.impact or 'NOT VERIFIED'}",
        "",
        "## What is not yet verified",
        "",
    ]
    for item in finding.missing_controls or ["(none listed)"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Evidence", ""])
    lines.extend(evidence_lines or ["- (no evidence records)"])
    lines.extend(
        [
            "",
            "## Recommended action",
            "",
            finding.recommended_action or "(none)",
            "",
            "## Verification requirements",
            "",
            "- Do not promote this to CONFIRMED / Verified impact without independent evidence.",
            "- Optional: `auctelis harden` for dry-run patches; `auctelis watch` for host authority.",
            "",
        ]
    )
    if finding.fix_snippet:
        lines.extend(["", "## Fix snippet", "", "```", finding.fix_snippet, "```", ""])
    if finding.verify_in_60s:
        lines.extend(
            [
                "",
                "## What would change this verdict",
                "",
                finding.verify_in_60s,
                "",
            ]
        )
    return "\n".join(lines)


def render_markdown_summary(scan: ScanResult, *, terminal: str | None = None) -> str:
    summary = terminal if terminal is not None else render_terminal_report(scan)
    ordered = _ordered_findings(scan.findings)
    lines = [
        "# auctelis — decision report",
        "",
        "Decision-oriented scan summary. Capability observations are not vulnerabilities.",
        "Absence of findings is not evidence of safety when coverage is incomplete.",
        "",
        "```text",
        summary.rstrip(),
        "```",
        "",
        "## Critical / high findings",
        "",
    ]
    critical = [f for f in ordered if is_high_gate_finding(f)]
    if not critical:
        lines.append("None at CRITICAL/HIGH for SECURITY_FINDING or EXPOSURE.")
    else:
        for finding in critical:
            lines.append(
                f"- **{finding.finding_id}** "
                f"[{finding.finding_class}/{finding.severity}/{finding.confidence}] "
                f"{finding.title}"
            )
            lines.append(f"  - Evidence: `{_evidence_path(scan, finding) or 'n/a'}`")
            lines.append(f"  - Action: {finding.recommended_action}")

    lines.extend(["", "## All findings", ""])
    if not scan.findings:
        lines.append("No deterministic findings.")
    else:
        for finding in ordered:
            lines.append(
                f"- **{finding.finding_id}** "
                f"[{finding.finding_class}/{finding.severity}/{finding.confidence}] "
                f"{finding.title}"
            )
            lines.append(f"  - {finding.recommended_action}")

    lines.extend(
        [
            "",
            "## Unverified areas",
            "",
        ]
    )
    for item in scan.coverage.get("not_verified") or []:
        lines.append(f"- {item}")
    for family in scan.coverage.get("manual_review_families") or []:
        lines.append(f"- Manual-only family: {family}")

    lines.extend(
        [
            "",
            "## Residual risk questions (human judgment required)",
            "",
            "1. What authority does this ecosystem introduce, and who receives it?",
            "2. What newly changed since the baseline?",
            "3. What must be fixed before install / merge / deploy?",
            "4. What remains unverified and must be explicitly accepted?",
            "",
        ]
    )
    return "\n".join(lines)
