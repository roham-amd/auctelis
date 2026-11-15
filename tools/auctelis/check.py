"""Repo-only authority check — the product front door.

``auctelis check`` inventories agent configs in a repository, compares them to
the committed ``AUTHORITY.lock``, and prints the authority delta. No host home
scan, no allow store, no hooks.

Schema: ``authority-diff/1`` (JSON via ``--json``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from auctelis.authority_card import (
    delta_cards,
    highlight_cards,
    kind_label,
    sealable_records,
)
from auctelis.authority_lock import (
    LOCK_NAME,
    build_authority_lock,
    default_lock_path,
    delta_label,
    diff_authority_locks,
)
from auctelis.lock_io import AuthorityLockError, load_authority_lock
from auctelis.security.engine import ScanResult, run_authority_inventory

_EMPTY_LOCK: dict[str, Any] = {
    "version": 1,
    "records": [],
    "policy_hash": None,
    "mcp_tools": {},
}

_REACH_KEYS = (
    "mcp",
    "hook",
    "skill",
    "instructions",
    "command",
    "plugin",
    "subagent",
    "ci",
    "host",
    "other",
)

SCHEMA_VERSION = "authority-diff/1"


def _counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = dict.fromkeys(_REACH_KEYS, 0)
    for record in records:
        label = kind_label(record.get("kind"))
        if label == "agent host":
            continue
        if label in counts:
            counts[label] += 1
        else:
            counts["other"] += 1
    return counts


def _unparsed_count(scan: ScanResult | None) -> int:
    if scan is None:
        return 0
    coverage = scan.coverage if isinstance(scan.coverage, dict) else {}
    try:
        return int(coverage.get("unparsed_agent_config_count") or 0)
    except (TypeError, ValueError):
        return 0


def _gated_finding_count(scan: ScanResult | None) -> int:
    if scan is None:
        return 0
    from auctelis.security.gating import is_gate_finding

    return sum(1 for f in scan.findings if is_gate_finding(f))


def _family_coverage_line(scan: ScanResult | None) -> str:
    """Honest maturity counts — never present supported_ratio as a clearance %."""
    if scan is None:
        return "Coverage: (unavailable)"
    coverage = scan.coverage if isinstance(scan.coverage, dict) else {}
    by = coverage.get("component_counts_by_maturity") or {}
    supported = int(by.get("SUPPORTED") or 0)
    partial = int(by.get("PARTIAL") or 0)
    manual = int(by.get("MANUAL_ONLY") or 0)
    unsupported = int(by.get("UNSUPPORTED") or 0)
    unparsed = _unparsed_count(scan)
    return (
        f"Coverage: SUPPORTED {supported} · PARTIAL {partial} · "
        f"MANUAL_ONLY {manual} · UNSUPPORTED {unsupported}"
        + (f" · NOT PARSED {unparsed}" if unparsed else "")
    )


def build_check_report(
    root: Path | None = None,
    *,
    lock_file: Path | None = None,
) -> tuple[dict[str, Any], list[str], ScanResult | None]:
    """Return ``(report, cards, scan)`` for repo authority vs ``AUTHORITY.lock``."""
    repo = (root or Path.cwd()).expanduser().resolve()
    lock_path = lock_file.expanduser().resolve() if lock_file else default_lock_path(repo)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "repository": str(repo),
        "lock_path": str(lock_path),
        "lock_present": False,
        "counts": dict.fromkeys(_REACH_KEYS, 0),
        "delta": {},
        "label": "NONE",
        "verdict": "QUIET",
        "meaningful": False,
        "unparsed": 0,
        "gated_findings": 0,
        "empty": False,
        "first_run": False,
        "inventory_total": 0,
        "highlight_total": 0,
        "error": None,
        "coverage_line": "",
    }

    scan = run_authority_inventory(repo)
    head = build_authority_lock(repo, scan=scan)
    head_records = list(head.get("records") or [])
    sealable = sealable_records(head_records)
    report["counts"] = _counts(head_records)
    report["unparsed"] = _unparsed_count(scan)
    report["gated_findings"] = _gated_finding_count(scan)
    report["coverage_line"] = _family_coverage_line(scan)
    report["coverage"] = scan.coverage if isinstance(scan.coverage, dict) else {}
    report["inventory_total"] = len(sealable)
    report["empty"] = len(sealable) == 0

    base = dict(_EMPTY_LOCK)
    if lock_path.is_file():
        report["lock_present"] = True
        try:
            base = load_authority_lock(lock_path)
        except AuthorityLockError as exc:
            report["error"] = str(exc)
            report["verdict"] = "FAIL_CLOSED"
            return report, [], scan
    else:
        report["first_run"] = True
        cards, highlight_total, inventory_total = highlight_cards(head_records)
        report["highlight_total"] = highlight_total
        report["inventory_total"] = inventory_total
        report["meaningful"] = False
        report["label"] = "NONE"
        report["verdict"] = "BASELINE_NEEDED"
        if report["unparsed"]:
            report["meaningful"] = True
            report["verdict"] = "NEEDS_REVIEW"
            report["label"] = "GROWTH"
        report["delta"] = {
            "summary": {
                "added": inventory_total,
                "removed": 0,
                "changed": 0,
                "meaningful_authority_change": False,
                "authority_changed": False,
                "policy_changed": False,
            },
            "changes": {"added": sealable, "removed": [], "changed": []},
        }
        return report, cards, scan

    delta = diff_authority_locks(base, head)
    summary = dict(delta.get("summary") or {})
    cards = delta_cards(delta, limit=12)
    # Align with lock --check: representation path/digest drift is also review.
    lock_drift = bool(summary.get("authority_changed"))
    meaningful = bool(cards or summary.get("policy_changed") or lock_drift)
    unparsed = int(report["unparsed"] or 0)
    if unparsed:
        meaningful = True
    report["delta"] = delta
    report["label"] = delta_label(summary) if meaningful else "NONE"
    report["meaningful"] = meaningful
    if meaningful:
        # One vocabulary: any meaningful lock drift needing human review is
        # NEEDS_REVIEW (GROWTH / REDUCTION / mixed). AUTHORITY_CHANGED is retired.
        report["verdict"] = "NEEDS_REVIEW"
    else:
        report["verdict"] = "LOCKED"
    return report, cards, scan


def why_repo(
    query: str,
    *,
    root: Path | None = None,
) -> tuple[list[str], int]:
    """Resolve ``auctelis why <name>`` against the current repository."""
    from auctelis.authority_card import find_records_by_name, why_record

    repo = (root or Path.cwd()).expanduser().resolve()
    scan = run_authority_inventory(repo)
    head = build_authority_lock(repo, scan=scan)
    matches = find_records_by_name(list(head.get("records") or []), query)
    if not matches:
        return [f'auctelis why: no authority record matched "{query}"'], 1
    lines: list[str] = []
    for record in matches[:5]:
        lines.extend(why_record(record))
        lines.append("")
    if len(matches) > 5:
        lines.append(f"… +{len(matches) - 5} more matches")
    return lines, 0


def _inventory_line(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    total = int(report.get("inventory_total") or 0)
    bits = []
    for key, label in (
        ("mcp", "MCP"),
        ("skill", "skills"),
        ("instructions", "instructions"),
        ("hook", "hooks"),
        ("command", "commands"),
        ("plugin", "plugins"),
        ("subagent", "subagents"),
        ("ci", "CI"),
        ("host", "host"),
        ("other", "other"),
    ):
        n = int(counts.get(key) or 0)
        if n:
            bits.append(f"{n} {label}")
    detail = ", ".join(bits) if bits else "no authority records"
    return f"Inventory: {total} records ({detail})."


def render_check(
    report: dict[str, Any],
    cards: list[str] | None = None,
) -> str:
    """Render the one-screen repo authority check."""
    error = report.get("error")
    if error:
        return f"auctelis check: {error}\nFail-closed: fix or reseal {LOCK_NAME}."

    lines: list[str] = []
    repo = report.get("repository") or "."
    verdict = report.get("verdict") or "QUIET"
    label = report.get("label") or "NONE"
    unparsed = int(report.get("unparsed") or 0)

    coverage_line = str(report.get("coverage_line") or "")
    gated = int(report.get("gated_findings") or 0)

    def _coverage_footer() -> list[str]:
        out: list[str] = []
        if coverage_line:
            out.append(coverage_line)
        # Inventory-only product path: findings are advisory research, not a gate.
        if gated:
            out.append(
                f"Advisory findings: {gated}"
                + (f" · NOT PARSED: {unparsed}" if unparsed else "")
                + " (not a gate input; see auctelis-dev scan)"
            )
        elif unparsed:
            out.append(f"NOT PARSED: {unparsed}")
        out.append(f"{LOCK_NAME} match is declared-config only — not a security clearance.")
        return out

    if report.get("first_run"):
        lines.append(f"auctelis check · {repo}")
        lines.append(_inventory_line(report))
        if cards:
            lines.append("")
            lines.extend(cards[:12])
            more = len(cards) - 12
            if more > 0:
                lines.append(f"… +{more} more")
        lines.append("")
        lines.append(f"Verdict: {verdict} · label {label}")
        lines.append(f"Next: auctelis lock --update  # write {LOCK_NAME}, then commit")
        lines.extend(_coverage_footer())
        return "\n".join(lines)

    if not report.get("meaningful"):
        lines.append(f"auctelis check · {LOCK_NAME} matches · {label}")
        lines.extend(_coverage_footer())
        return "\n".join(lines)

    lines.append(f"auctelis check · {verdict} · {label}")
    if unparsed:
        lines.append(f"NOT PARSED: {unparsed} agent config(s) — lock match is not clearance.")
    if cards:
        lines.extend(cards)
    else:
        summary = (report.get("delta") or {}).get("summary") or {}
        if summary.get("policy_changed"):
            lines.append("~ policy: .auctelis.yml changed")
        elif summary.get("authority_changed"):
            lines.append("~ representation drift (path/digest) — reseal AUTHORITY.lock")
    lines.append("")
    lines.append(f"Next: review the delta, then `auctelis lock --update` and commit {LOCK_NAME}")
    lines.extend(_coverage_footer())
    return "\n".join(lines)


def check_exit_code(report: dict[str, Any]) -> int:
    """Exit 0 quiet/first-run, 1 authority delta / unparsed, 2 lock error."""
    if report.get("error"):
        return 2
    if report.get("meaningful") or int(report.get("unparsed") or 0):
        return 1
    return 0
