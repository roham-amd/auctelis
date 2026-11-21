"""Repo-only authority check — the product front door.

``auctelis check`` inventories agent configs in a repository and prints a ranked
reach report. When ``AUTHORITY.lock`` is present it diffs against that baseline;
when absent it runs lockless (JSON verdict ``BASELINE_NEEDED``). No host home
scan, no allow store, no hooks.

Schema: ``authority-diff/1`` (JSON via ``--json``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from auctelis.authority_card import (
    delta_cards,
    find_records_by_name,
    highlight_cards,
    kind_label,
    pin_report,
    reach_snapshot,
    sealable_records,
    why_record,
)
from auctelis.authority_lock import (
    LOCK_NAME,
    STRICT_DIGEST_ADVISORY,
    build_authority_lock,
    default_lock_path,
    delta_label,
    diff_authority_locks,
)
from auctelis.lock_io import AuthorityLockError, empty_authority_lock, load_authority_lock
from auctelis.security.engine import ScanResult, run_authority_inventory
from auctelis.textutil import sanitize_terminal_line, strip_control
from auctelis.versioning import product_version, pypi_live

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


def attach_launcher_args(records: list[dict[str, Any]], scan: ScanResult | None) -> None:
    """Copy inventory ``args`` onto sealed records for pin doctor (not persisted)."""
    if scan is None:
        return
    by_key: dict[tuple[str, str], list[Any]] = {}
    for comp in scan.inventory.get("components") or []:
        if not isinstance(comp, dict):
            continue
        raw_args = comp.get("args")
        if not isinstance(raw_args, list) or not raw_args:
            continue
        path = str(comp.get("repository_path") or "").replace("\\", "/")
        name = str(comp.get("name") or "")
        by_key[(path, name)] = list(raw_args)
    for rec in records:
        key = (str(rec.get("path") or "").replace("\\", "/"), str(rec.get("name") or ""))
        if key in by_key:
            rec["args"] = by_key[key]


def attach_launcher_args_to_delta(
    delta: dict[str, Any] | None,
    records: list[dict[str, Any]],
) -> None:
    """Copy ephemeral ``args`` onto delta added/after records for pin doctor.

    ``diff_authority_locks`` normalizes records and drops ``args``; rehydrate
    from the already-attached head inventory so live PR ``Pin fix`` keeps argv.
    """
    by_key: dict[tuple[str, str], list[Any]] = {}
    for rec in records:
        raw_args = rec.get("args")
        if not isinstance(raw_args, list) or not raw_args:
            continue
        key = (str(rec.get("path") or "").replace("\\", "/"), str(rec.get("name") or ""))
        by_key[key] = list(raw_args)
    if not by_key or not isinstance(delta, dict):
        return
    raw_changes = delta.get("changes")
    changes: dict[str, Any] = raw_changes if isinstance(raw_changes, dict) else {}
    for rec in changes.get("added") or []:
        if not isinstance(rec, dict):
            continue
        key = (str(rec.get("path") or "").replace("\\", "/"), str(rec.get("name") or ""))
        if key in by_key:
            rec["args"] = by_key[key]
    for item in changes.get("changed") or []:
        if not isinstance(item, dict):
            continue
        after = item.get("after")
        if not isinstance(after, dict):
            continue
        key = (str(after.get("path") or "").replace("\\", "/"), str(after.get("name") or ""))
        if key in by_key:
            after["args"] = by_key[key]


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
    from auctelis.inventory.coverage import unparsed_agent_config_count_from_coverage

    return unparsed_agent_config_count_from_coverage(
        scan.coverage if isinstance(scan.coverage, dict) else {}
    )


def _gated_finding_count(scan: ScanResult | None) -> int:
    if scan is None:
        return 0
    from auctelis.security.gating import is_gate_finding

    return sum(1 for f in scan.findings if is_gate_finding(f))


def _family_coverage_line(scan: ScanResult | None) -> str:
    """Honest maturity counts — never present supported_ratio as a clearance %."""
    from auctelis.inventory.coverage import family_coverage_line_from_coverage

    if scan is None:
        return family_coverage_line_from_coverage(None)
    coverage = scan.coverage if isinstance(scan.coverage, dict) else {}
    return family_coverage_line_from_coverage(coverage, unparsed=_unparsed_count(scan))


def build_check_report(
    root: Path | None = None,
    *,
    lock_file: Path | None = None,
    top: int = 5,
    limits: object | None = None,
    strict_digests: bool = False,
) -> tuple[dict[str, Any], list[str], ScanResult | None]:
    """Return ``(report, cards, scan)`` for repo authority vs ``AUTHORITY.lock``.

    When ``strict_digests`` is false (default), plain-CI / prose representation
    digest drift is advisory only (AUCT-034).
    """
    from auctelis.inventory.limits import CollectorLimits

    repo = (root or Path.cwd()).expanduser().resolve()
    lock_path = lock_file.expanduser().resolve() if lock_file else default_lock_path(repo)
    scan_limits = limits if isinstance(limits, CollectorLimits) else None

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
        "reach": {},
        "pins": {},
    }

    # AUCT-031: local git origin → owner/repo Watch links (non-fatal).
    from auctelis.github_audit import infer_local_github_watch_meta

    watch_meta = infer_local_github_watch_meta(repo)
    if watch_meta.get("repository"):
        report["repository"] = str(watch_meta["repository"])
    if watch_meta.get("github_web_base"):
        report["github_web_base"] = str(watch_meta["github_web_base"])
    if watch_meta.get("default_branch"):
        report["default_branch"] = str(watch_meta["default_branch"])
    if "already_watching" in watch_meta:
        report["already_watching"] = bool(watch_meta["already_watching"])

    from auctelis.reach_tiers import load_trusted_hosts

    trusted_hosts = load_trusted_hosts(repo)
    scan = run_authority_inventory(repo, limits=scan_limits)
    head = build_authority_lock(repo, scan=scan)
    head_records = list(head.get("records") or [])
    attach_launcher_args(head_records, scan)
    sealable = sealable_records(head_records)
    report["reach"] = reach_snapshot(
        head_records,
        limit=top,
        trusted_hosts=trusted_hosts,
    )
    report["pins"] = pin_report(head_records)
    report["counts"] = _counts(head_records)
    report["unparsed"] = _unparsed_count(scan)
    report["gated_findings"] = _gated_finding_count(scan)
    report["coverage_line"] = _family_coverage_line(scan)
    report["coverage"] = scan.coverage if isinstance(scan.coverage, dict) else {}
    report["inventory_total"] = len(sealable)
    report["empty"] = len(sealable) == 0

    base = empty_authority_lock()
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
        # Counts only; cards come from the ranked reach snapshot unless the
        # caller explicitly asked for the full first-run inventory (--top 0
        # means hide cards, so no render is needed there either).
        _unused_cards, highlight_total, inventory_total = highlight_cards(head_records, limit=0)
        report["highlight_total"] = highlight_total
        report["inventory_total"] = inventory_total
        cards = list(report["reach"].get("top_cards") or [])
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

    delta = diff_authority_locks(base, head, trusted_hosts=trusted_hosts)
    summary = dict(delta.get("summary") or {})
    cards = delta_cards(delta, limit=12, trusted_hosts=trusted_hosts)
    # Align with lock --check: meaningful / Hook drift fails; plain
    # representation digest drift is advisory unless --strict-digests (AUCT-034).
    authority_changed = bool(summary.get("authority_changed"))
    strict_drift_only = bool(summary.get("strict_drift_only"))
    lock_drift = authority_changed and (strict_digests or not strict_drift_only)
    meaningful = bool(cards or summary.get("policy_changed") or lock_drift)
    unparsed = int(report["unparsed"] or 0)
    if unparsed:
        meaningful = True
    report["delta"] = delta
    report["strict_digests"] = bool(strict_digests)
    report["strict_drift_only"] = strict_drift_only
    report["label"] = delta_label(summary) if meaningful else "NONE"
    report["meaningful"] = meaningful
    if not meaningful:
        # Quiet lock match still shows what the repo can reach — the card is
        # the product, not a one-line "matches".
        cards = list((report.get("reach") or {}).get("top_cards") or [])
        if authority_changed and strict_drift_only and not strict_digests:
            report["advisory"] = STRICT_DIGEST_ADVISORY
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
    repo = (root or Path.cwd()).expanduser().resolve()
    scan = run_authority_inventory(repo)
    head = build_authority_lock(repo, scan=scan)
    matches = find_records_by_name(list(head.get("records") or []), query)
    if not matches:
        return [f'auctelis why: no authority record matched "{strip_control(query)}"'], 1
    lines: list[str] = []
    for record in matches[:5]:
        lines.extend(why_record(record))
        lines.append("")
    if len(matches) > 5:
        lines.append(f"… +{len(matches) - 5} more matches")
    return [sanitize_terminal_line(line) for line in lines], 0


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
    noun = "record" if total == 1 else "records"
    return f"Inventory: {total} {noun} ({detail})."


def _reach_line(report: dict[str, Any]) -> str:
    reach = report.get("reach") or {}
    total = int(reach.get("total") or 0)
    if not total:
        return ""
    counts = reach.get("tier_counts") or {}
    t2 = int(counts.get("tier2") or 0)
    t1 = int(counts.get("tier1") or 0)
    t0 = int(counts.get("tier0") or 0)
    noun = "record" if total == 1 else "records"
    return f"Reach: {total} {noun} · tier 2 fail {t2} · tier 1 comment {t1} · tier 0 silent {t0}"


def _cli_prefix() -> str:
    """Copy-pasteable CLI invocation (bare name when PyPI is live, else uvx git)."""
    if pypi_live():
        return "auctelis"
    ver = product_version()
    return (
        f'uvx --from "git+https://github.com/roham-amd/auctelis.git@v{ver}'
        f'#subdirectory=tools" auctelis'
    )


def _pins_line(report: dict[str, Any]) -> str:
    pins = report.get("pins") or {}
    unpinned = int(pins.get("unpinned") or 0)
    total = int(pins.get("total") or 0)
    if not unpinned:
        return ""
    # "1 of 2 MCP servers": the noun agrees with the total, not the subset.
    noun = "server" if total == 1 else "servers"
    prefix = _cli_prefix()
    return (
        f"Pins: {unpinned} of {total} MCP {noun} unpinned (run `{prefix} check --pins` for fixes)"
    )


def _next_step_line() -> str:
    """First-run footer: bare ``auctelis`` only when PyPI is live."""
    prefix = _cli_prefix()
    if pypi_live():
        return (
            f"Next: {prefix} init --lockless  # one-file comment-only PR Watch, or "
            f"{prefix} check --report out/ for an HTML/MD/JSON Reach Report"
        )
    return (
        f"Next: {prefix} check --report out/ for an HTML/MD/JSON Reach Report, or "
        f"{prefix} init --lockless"
    )


def render_pin_report(report: dict[str, Any]) -> str:
    """Detailed MCP pin doctor output for ``check --pins``."""
    pins = report.get("pins") or {}
    items = list(pins.get("items") or [])
    if not items:
        total = int(pins.get("total") or 0)
        return f"No unpinned MCP servers ({total} checked)."
    lines = [f"Unpinned MCP servers: {len(items)} of {int(pins.get('total') or 0)}"]
    for item in items:
        where = f" @ {item['path']}" if item.get("path") else ""
        env = f" · env {', '.join(item['env_keys'])}" if item.get("env_keys") else ""
        lines.append(f"  {item['name']}{where} · pin {item['pin_state']}{env}")
        lines.append(f"    → {item['suggestion']}")
        snippet = str(item.get("config_snippet") or "").strip()
        if snippet:
            lines.append(f"    config: {snippet}")
    return "\n".join(sanitize_terminal_line(line) for line in lines)


def _terminal(lines: list[str]) -> str:
    """Join CLI output, stripping control/bidi characters from repo-controlled text."""
    return "\n".join(sanitize_terminal_line(line) for line in lines)


def render_check(
    report: dict[str, Any],
    cards: list[str] | None = None,
) -> str:
    """Render the one-screen repo authority check."""
    error = report.get("error")
    if error:
        return _terminal([f"auctelis check: {error}", f"Fail-closed: fix or reseal {LOCK_NAME}."])

    lines: list[str] = []
    repo = report.get("repository") or "."
    verdict = report.get("verdict") or "QUIET"
    label = report.get("label") or "NONE"
    unparsed = int(report.get("unparsed") or 0)

    coverage_line = str(report.get("coverage_line") or "")
    gated = int(report.get("gated_findings") or 0)

    lock_present = bool(report.get("lock_present"))

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
        if lock_present:
            out.append(f"{LOCK_NAME} match is declared-config only — not a security clearance.")
        else:
            out.append(
                "Passive scan — declared config only; publisher identity and "
                "runtime behavior are NOT VERIFIED."
            )
        return out

    if report.get("first_run"):
        lines.append(f"auctelis check · {repo}")
        lines.append(_inventory_line(report))
        reach_line = _reach_line(report)
        if reach_line:
            lines.append(reach_line)
        if cards:
            lines.append("")
            lines.extend(cards)
            hidden = int(report.get("inventory_total") or 0) - len(cards)
            if hidden > 0:
                lines.append(
                    f"… +{hidden} more (see `{_cli_prefix()} check --top {hidden + len(cards)}`)"
                )
        pins_line = _pins_line(report)
        if pins_line:
            lines.append(pins_line)
        lines.append("")
        # Keep JSON verdict BASELINE_NEEDED; terminal clarifies lockless mode.
        if verdict == "BASELINE_NEEDED" and not lock_present:
            lines.append(f"Mode: lockless (no {LOCK_NAME}) · label {label}")
        else:
            lines.append(f"Verdict: {verdict} · label {label}")
        lines.append(_next_step_line())
        lines.extend(_coverage_footer())
        return _terminal(lines)

    if not report.get("meaningful"):
        lines.append(f"auctelis check · {LOCK_NAME} matches · {label}")
        advisory = report.get("advisory")
        if advisory:
            lines.append(f"Note: {advisory}")
        reach_line = _reach_line(report)
        if reach_line:
            lines.append(reach_line)
        if cards:
            lines.append("")
            lines.extend(cards)
        pins_line = _pins_line(report)
        if pins_line:
            lines.append(pins_line)
        lines.extend(_coverage_footer())
        return _terminal(lines)

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
    pins_line = _pins_line(report)
    if pins_line:
        lines.append(pins_line)
    lines.append("")
    lines.append(
        f"Next: review the delta, then `{_cli_prefix()} lock --update` and commit {LOCK_NAME}"
    )
    lines.extend(_coverage_footer())
    return _terminal(lines)


def check_exit_code(report: dict[str, Any]) -> int:
    """Exit 0 quiet/first-run, 1 authority delta / unparsed, 2 lock error."""
    if report.get("error"):
        return 2
    if report.get("meaningful") or int(report.get("unparsed") or 0):
        return 1
    return 0
