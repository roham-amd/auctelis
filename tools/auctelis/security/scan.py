"""Write auctelis scan artifacts and optional SARIF / baseline diff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from auctelis.export.authority_sbom import build_authority_sbom
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.export.sarif import findings_doc_to_sarif
from auctelis.jsonio import write_json, write_text
from auctelis.paths import resolve_default_output_dir
from auctelis.policy import AuctelisPolicy
from auctelis.security.authority import (
    build_authority_snapshot,
    diff_authority_snapshots,
    render_component_delta_lines,
)
from auctelis.security.baseline import diff_against_baseline, load_baseline, save_baseline
from auctelis.security.engine import ScanResult, run_security_scan
from auctelis.security.gating import compute_exit_code
from auctelis.security.report import render_markdown_summary, render_terminal_report


def write_scan_artifacts(
    scan: ScanResult,
    output_dir: Path,
    *,
    risk_delta: dict[str, Any] | None = None,
    risk_delta_doc: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    authority_delta: dict[str, Any] | None = None,
    lock_delta: dict[str, Any] | None = None,
    policy_mode: str | None = None,
    suppressions: list[dict[str, str]] | None = None,
    target_policy_ignored: bool = False,
    full_report: bool = False,
) -> dict[str, Any]:
    """Persist product-shaped scan artifacts.

    Default (Authority Diff product path): findings, PR comment, short summary,
    SARIF, and authority snapshot/delta when present.

    Pass ``full_report=True`` (``auctelis scan --full``) for inventory, graph,
    capabilities, long markdown/text reports, and profile metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    findings_doc = scan.to_findings_doc()
    if suppressions:
        findings_doc["suppressions"] = suppressions
        findings_doc["suppression_count"] = len(suppressions)
    findings_doc["target_policy_ignored"] = target_policy_ignored
    summary = render_terminal_report(scan, risk_delta=risk_delta, full=full_report)
    # Product defaults: Authority Diff surfaces + inventory (needed by CI diffs/locks).
    write_json(output_dir / "findings.json", findings_doc)
    write_json(output_dir / "inventory.json", scan.inventory)
    if authority_snapshot is not None:
        write_json(output_dir / "authority-snapshot.json", authority_snapshot)
    if authority_delta is not None:
        write_json(output_dir / "authority-delta.json", authority_delta)
    write_text(output_dir / "scan-summary.txt", summary)
    write_json(output_dir / "findings.sarif.json", findings_doc_to_sarif(findings_doc))
    comment = render_authority_diff_comment(
        findings_doc,
        risk_delta=risk_delta_doc,
        authority_delta=authority_delta,
        authority_snapshot=authority_snapshot,
        lock_delta=lock_delta,
        policy_mode=policy_mode,
    )
    write_text(output_dir / "pr-comment.md", comment)
    write_json(output_dir / "authority-sbom.json", build_authority_sbom(scan))

    if full_report:
        full_summary = render_terminal_report(scan, risk_delta=risk_delta, full=True)
        write_json(output_dir / "ecosystem-graph.json", scan.graph)
        write_json(output_dir / "capabilities.json", {"capabilities": findings_doc["capabilities"]})
        write_text(
            output_dir / "scan-report.md",
            render_markdown_summary(scan, terminal=full_summary),
        )
        write_text(output_dir / "scan-summary-full.txt", full_summary)
        write_json(
            output_dir / "profile.json",
            {
                "auctelis_audit_profile": "scan",
                "product": "auctelis",
                "product_version": scan.product_version,
                "package_version": scan.package_version,
                "purpose": "Authority Diff + deterministic security observations",
                "deliverable": "PR comment, findings, inventory, SARIF; --full adds graph/report",
                "rules_applied": scan.rules_applied,
                "limitations": findings_doc["limitations"],
            },
        )
    return {
        "output_dir": str(output_dir),
        "finding_count": len(scan.findings),
        "component_count": len(scan.inventory.get("components") or []),
        "summary": summary,
        "pr_comment": comment,
        "suppressions": suppressions or [],
        "target_policy_ignored": target_policy_ignored,
        "full_report": full_report,
    }


def _evidence_paths(scan: ScanResult, finding_evidence_ids: list[str]) -> list[str]:
    wanted = set(finding_evidence_ids)
    return [ev.file_path for ev in scan.evidences if ev.evidence_id in wanted and ev.file_path]


def apply_suppressions(scan: ScanResult, policy: AuctelisPolicy | None) -> list[dict[str, str]]:
    """Mark matching findings ``suppressed: true`` (keep in artifacts); return audit records.

    Findings are never deleted: JSON / digests / SARIF retain them with an explicit
    suppression record so a target policy cannot silently blind an auditor.
    """
    if policy is None or not policy.suppressions:
        return []
    records: list[dict[str, str]] = []
    for finding in scan.findings:
        match = policy.applies_to_finding(
            rule_id=finding.rule_id,
            evidence_paths=_evidence_paths(scan, finding.evidence_ids),
        )
        if match is None:
            continue
        record = {
            "finding_id": finding.finding_id,
            "rule_id": finding.rule_id,
            "path": match.path,
            "justification": match.justification,
            "owner": match.owner,
        }
        finding.suppressed = True
        finding.suppression = dict(record)
        records.append(record)
    return records


def run_scan(
    target: Path,
    *,
    output_dir: Path | None = None,
    baseline: Path | None = None,
    save_baseline_path: Path | None = None,
    fail_on: str | None = None,
    policy: AuctelisPolicy | None = None,
    target_policy_ignored: bool = False,
    full_report: bool = False,
    default_excludes: bool = True,
) -> tuple[ScanResult, dict[str, Any], int]:
    """Run scan; return (scan, payload, exit_code).

    Default ``output_dir`` is ``./auctelis-out`` relative to the process cwd — not
    ``<target>/auctelis-out`` — so scanning an external repository stays read-only
    with respect to the target tree.
    """
    scan = run_security_scan(target, default_excludes=default_excludes)
    suppressed = apply_suppressions(scan, policy)
    out = (output_dir or resolve_default_output_dir()).resolve()
    out.mkdir(parents=True, exist_ok=True)

    authority_snapshot = build_authority_snapshot(scan)
    authority_delta: dict[str, Any] | None = None

    risk_delta_summary: dict[str, Any] | None = None
    risk_delta_doc: dict[str, Any] | None = None
    if baseline and baseline.is_file():
        baseline_doc = load_baseline(baseline)
        risk_delta_doc = diff_against_baseline(scan, baseline_doc)
        write_json(out / "risk-delta.json", risk_delta_doc)
        risk_delta_summary = risk_delta_doc["summary"]
        if baseline_doc.get("authority_snapshot"):
            authority_delta = diff_authority_snapshots(
                baseline_doc["authority_snapshot"], authority_snapshot
            )
            risk_delta_doc["authority_delta"] = authority_delta
            risk_delta_doc["component_delta_lines"] = render_component_delta_lines(authority_delta)

    policy_mode = policy.mode if policy is not None else None
    payload = write_scan_artifacts(
        scan,
        out,
        risk_delta=risk_delta_summary,
        risk_delta_doc=risk_delta_doc,
        authority_snapshot=authority_snapshot,
        authority_delta=authority_delta,
        policy_mode=policy_mode,
        suppressions=suppressed,
        target_policy_ignored=target_policy_ignored,
        full_report=full_report,
    )
    if risk_delta_summary is not None:
        payload["risk_delta"] = risk_delta_summary
    if risk_delta_doc is not None:
        payload["risk_delta_doc"] = risk_delta_doc
    if authority_delta is not None:
        payload["authority_delta"] = authority_delta

    if suppressed:
        write_json(out / "suppressions.json", {"suppressions": suppressed})
        payload["suppressions"] = suppressed
    if policy and policy.source_path:
        payload["policy_path"] = str(policy.source_path)
        payload["policy_mode"] = policy.mode
    review_classes = list(policy.require_review) if policy and policy.require_review else []
    if review_classes:
        from auctelis.security.review_classes import require_review_hits

        hits = require_review_hits(scan.findings, review_classes)
        payload["require_review"] = review_classes
        payload["require_review_hits"] = hits

    if save_baseline_path is not None:
        doc = save_baseline(scan, save_baseline_path)
        doc["authority_snapshot"] = authority_snapshot
        write_json(save_baseline_path, doc)
        payload["baseline_saved"] = str(save_baseline_path)

    exit_code = compute_exit_code(
        fail_on,
        findings=scan.findings,
        risk_delta_summary=risk_delta_summary,
        coverage=scan.coverage if isinstance(getattr(scan, "coverage", None), dict) else None,
        require_review=review_classes or None,
    )
    return scan, payload, exit_code
