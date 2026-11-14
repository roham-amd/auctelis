"""Authority Watch — the one-screen declared-config delta.

``auctelis watch`` is the first screen: it inventories the host agent configs
(Cursor, Claude Code, VS Code, …), compares them with the last human seal in
``~/.auctelis/AUTHORITY.lock``, and prints one line per authority change.

- No lock yet → summary counts + highlight new destinations / executables /
  secrets; the rest collapses behind an inventory line. Seal is the next step.
- Lock present and unchanged → quiet (the second-session experience).
- Lock present and changed → the delta, and a human chooses reseal or revert.
"""

from __future__ import annotations

import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from auctelis.authority_card import (
    count_cards,
    delta_cards,
    highlight_cards,
    kind_label,
)
from auctelis.authority_lock import (
    build_authority_lock,
    delta_label,
    diff_authority_locks,
    home_lock_path,
    write_authority_lock,
)
from auctelis.host_scan import discover_host_surfaces, stage_all_host_surfaces
from auctelis.lock_io import AuthorityLockError, load_authority_lock
from auctelis.security.engine import ScanResult, run_security_scan

_EMPTY_LOCK: dict[str, Any] = {
    "version": 1,
    "records": [],
    "policy_hash": None,
    "mcp_tools": {},
}

_REACH_KEYS = ("mcp", "hook", "skill", "ci", "command", "other")


def _counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = dict.fromkeys(_REACH_KEYS, 0)
    for record in records:
        label = kind_label(record.get("kind"))
        if label in {"agent host", "host"}:
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


def _surface_ids(surfaces: list[Any]) -> list[str]:
    return sorted({str(s.host_id) for s in surfaces if getattr(s, "exists", False)})


def build_watch_report(
    *,
    home: Path | None = None,
    lock_file: Path | None = None,
) -> tuple[dict[str, Any], list[str], ScanResult | None]:
    """Return ``(report, delta_cards, scan)`` for the current host.

    ``delta_cards`` are pre-rendered so the session hook can print a one-line
    delta without re-reading the lock. On first run (no seal) they are the
    highlight cards (destinations / executables / secrets), not the full inventory.
    """
    home_root = (home or Path.home()).expanduser().resolve()
    lock_path = home_lock_path(home_root, lock_file=lock_file)
    surfaces = discover_host_surfaces(home=home_root)
    present = [s for s in surfaces if s.exists]

    report: dict[str, Any] = {
        "schema_version": "watch-report/1",
        "home": str(home_root),
        "lock_path": str(lock_path),
        "lock_present": False,
        "surfaces": [
            {"host_id": surface.host_id, "path": str(surface.path)} for surface in present
        ],
        "surface_ids": _surface_ids(present),
        "counts": dict.fromkeys(_REACH_KEYS, 0),
        "delta": {},
        "label": "NONE",
        "meaningful": False,
        "unparsed": 0,
        "empty": not present,
        "first_run": False,
        "inventory_total": 0,
        "highlight_total": 0,
        "error": None,
    }

    scan: ScanResult | None = None
    head: dict[str, Any] = dict(_EMPTY_LOCK)
    with ExitStack() as stack:
        synth, _staged = stage_all_host_surfaces(stack, home=home_root)
        scan = run_security_scan(synth)
        head = build_authority_lock(synth, scan=scan)

    head_records = list(head.get("records") or [])
    report["counts"] = _counts(head_records)
    report["unparsed"] = _unparsed_count(scan)

    base = dict(_EMPTY_LOCK)
    if lock_path.is_file():
        report["lock_present"] = True
        try:
            base = load_authority_lock(lock_path)
        except AuthorityLockError as exc:
            report["error"] = str(exc)
            return report, [], scan
    else:
        report["first_run"] = True
        cards, highlight_total, inventory_total = highlight_cards(head_records, limit=6)
        report["highlight_total"] = highlight_total
        report["inventory_total"] = inventory_total
        # First run is not a "delta" for exit codes / session hooks — sealing is.
        report["meaningful"] = False
        report["label"] = "NONE"
        report["delta"] = {
            "summary": {
                "added": inventory_total,
                "removed": 0,
                "changed": 0,
                "meaningful_authority_change": False,
                "authority_changed": False,
                "policy_changed": False,
            },
            "changes": {"added": head_records, "removed": [], "changed": []},
        }
        return report, cards, scan

    delta = diff_authority_locks(base, head)
    summary = dict(delta.get("summary") or {})
    cards = delta_cards(delta, limit=6)
    meaningful = bool(cards or summary.get("policy_changed"))
    report["delta"] = delta
    report["label"] = delta_label(summary) if meaningful else "NONE"
    report["meaningful"] = meaningful
    report["inventory_total"] = sum(
        1 for r in head_records if kind_label(r.get("kind")) not in {"agent host", "host"}
    )
    return report, cards, scan


def seal_home_lock(
    *,
    home: Path | None = None,
    lock_file: Path | None = None,
) -> dict[str, Any]:
    """Seal the current host authority. Human-only; never called by a hook."""
    home_root = (home or Path.home()).expanduser().resolve()
    lock_path = home_lock_path(home_root, lock_file=lock_file)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    surfaces = [s for s in discover_host_surfaces(home=home_root) if s.exists]

    if not surfaces:
        with tempfile.TemporaryDirectory(prefix="auctelis-empty-baseline-") as tmp:
            dest, lock = write_authority_lock(
                Path(tmp),
                path=lock_path,
                accept_gated=True,
            )
        return {"path": str(dest), "records": len(lock.get("records") or []), "empty": True}

    with ExitStack() as stack:
        synth, staged = stage_all_host_surfaces(stack, home=home_root)
        scan = run_security_scan(synth)
        dest, lock = write_authority_lock(
            synth,
            path=lock_path,
            accept_gated=True,
            scan=scan,
        )
    return {
        "path": str(dest),
        "records": len(lock.get("records") or []),
        "empty": not staged,
    }


def why_home(
    query: str,
    *,
    home: Path | None = None,
) -> tuple[list[str], int]:
    """Resolve ``auctelis why <name>`` against the current host inventory."""
    from auctelis.authority_card import find_records_by_name, why_record

    home_root = (home or Path.home()).expanduser().resolve()
    with ExitStack() as stack:
        synth, _staged = stage_all_host_surfaces(stack, home=home_root)
        scan = run_security_scan(synth)
        head = build_authority_lock(synth, scan=scan)
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


def _reach_line(counts: dict[str, int]) -> str:
    return (
        f"Reach: {counts.get('mcp', 0)} MCP, {counts.get('hook', 0)} hooks, "
        f"{counts.get('skill', 0)} skills, {counts.get('ci', 0)} CI"
    )


def _inventory_line(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    total = int(report.get("inventory_total") or 0)
    bits = []
    for key, label in (
        ("mcp", "MCP"),
        ("hook", "hooks"),
        ("skill", "skills"),
        ("command", "commands"),
        ("ci", "CI"),
    ):
        n = int(counts.get(key) or 0)
        if n:
            bits.append(f"{n} {label}")
    detail = ", ".join(bits) if bits else "no authority records"
    return f"Inventory: {total} records ({detail}). Seal to baseline."


def render_watch(
    report: dict[str, Any],
    cards: list[str] | None = None,
    *,
    command: str = "auctelis watch",
    delta_only: bool = False,
) -> str:
    """Render the one-screen authority watch (or just the delta lines)."""
    error = report.get("error")
    if delta_only:
        if error:
            return f"auctelis: {error}"
        if not report.get("lock_present") or not report.get("meaningful"):
            return ""
        lines = list(cards or [])
        if not lines:
            summary = (report.get("delta") or {}).get("summary") or {}
            if summary.get("policy_changed"):
                return "~ policy: .auctelis.yml changed"
            return ""
        total = count_cards(report.get("delta"))
        if total > len(lines):
            lines.append(f"… +{total - len(lines)} more")
        return "\n".join(lines)

    counts = report.get("counts") or {}
    surface_ids = report.get("surface_ids") or []
    lines = [f"{command} — declared agent authority on this machine"]

    if error:
        lines.append(f"Lock: unusable — {error}")
    elif report.get("lock_present"):
        lines.append(f"Lock: {report.get('lock_path')} (sealed)")
    else:
        lines.append(f"Lock: none yet ({report.get('lock_path')})")

    if report.get("empty"):
        lines.append(f"No host config found under {report.get('home')}.")
        lines.append(_reach_line(counts))
        lines.append("")
        lines.append("Empty baseline: seal when you are ready, or add an agent host config.")
        lines.append(
            "Next: `auctelis watch --seal` (then `auctelis watch --arm` for session tripwires)."
        )
        return "\n".join(lines)

    if surface_ids:
        lines.append(f"Found {len(surface_ids)} agent surface(s): {', '.join(surface_ids)}.")
    lines.append(_reach_line(counts))
    lines.append("")

    if error:
        lines.append("Fix or remove the lock, then re-run `auctelis watch`.")
        return "\n".join(lines)

    current_cards = list(cards or [])

    if report.get("first_run"):
        highlight_total = int(report.get("highlight_total") or 0)
        if current_cards:
            lines.append("New reach (destinations / executables / secrets) — not yet sealed:")
            lines.extend(current_cards)
            if highlight_total > len(current_cards):
                lines.append(f"… +{highlight_total - len(current_cards)} more highlights")
        else:
            lines.append("No new remote destinations, executables, or secrets detected.")
        lines.append(_inventory_line(report))
        lines.append("")
        unknown = "Unknown: publisher identity, effective permissions, runtime behavior."
        if int(report.get("unparsed") or 0):
            unknown += f" NOT PARSED: {report['unparsed']} agent config file(s)."
        lines.append(unknown)
        lines.append(
            "Next: seal this baseline → `auctelis watch --seal` "
            "(then `auctelis watch --arm`). Consent baseline, not a security clearance."
        )
        return "\n".join(lines)

    if not report.get("meaningful"):
        lines.append("No authority change since you sealed.")
    else:
        lines.append("Delta since you sealed:")

    if current_cards:
        lines.extend(current_cards)
        total = count_cards(report.get("delta"))
        if total > len(current_cards):
            lines.append(f"… +{total - len(current_cards)} more")
    elif (report.get("delta") or {}).get("summary", {}).get("policy_changed"):
        lines.append("~ policy: .auctelis.yml changed")
    lines.append("")

    unknown = "Unknown: publisher identity, effective permissions, runtime behavior."
    if int(report.get("unparsed") or 0):
        unknown += f" NOT PARSED: {report['unparsed']} agent config file(s)."
    lines.append(unknown)

    if report.get("meaningful"):
        lines.append("Next: review, then `auctelis watch --seal` to accept — or revert the config.")
        lines.append("Tip: `auctelis why <name>` prints the exact config path.")
    else:
        lines.append("Next: nothing to do; the hook speaks only when authority changes.")
    return "\n".join(lines)
