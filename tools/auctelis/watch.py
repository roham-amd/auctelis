"""Authority Watch — the one-screen declared-config delta.

``auctelis watch`` is the first screen: it inventories the host agent configs
(Cursor, Claude Code, VS Code, …), compares them with the last human seal in
``~/.auctelis/AUTHORITY.lock``, and prints one line per authority change.

- No lock yet → every sealable record on screen + accept digest; seal is next.
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
    screen_digest,
    sealable_records,
)
from auctelis.authority_lock import (
    build_authority_lock,
    delta_label,
    diff_authority_locks,
    home_lock_path,
    write_authority_lock,
)
from auctelis.host_scan import (
    discover_host_surfaces,
    discover_project_surfaces,
    stage_watch_root,
)
from auctelis.lock_io import AuthorityLockError, load_authority_lock
from auctelis.security.engine import ScanResult, run_security_scan

_EMPTY_LOCK: dict[str, Any] = {
    "version": 1,
    "records": [],
    "policy_hash": None,
    "mcp_tools": {},
}

_REACH_KEYS = ("mcp", "hook", "skill", "ci", "command", "host", "other")


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


def _surface_ids(surfaces: list[Any]) -> list[str]:
    return sorted({str(s.host_id) for s in surfaces if getattr(s, "exists", False)})


def build_watch_report(
    *,
    home: Path | None = None,
    lock_file: Path | None = None,
    project: Path | None = None,
) -> tuple[dict[str, Any], list[str], ScanResult | None]:
    """Return ``(report, delta_cards, scan)`` for the current host (+ project).

    ``delta_cards`` are pre-rendered so the session hook can print a one-line
    delta without re-reading the lock. On first run every sealable record is
    shown (Host Settings included) so seal never hides posture.
    """
    home_root = (home or Path.home()).expanduser().resolve()
    # Library callers may omit project (home-only). The CLI always passes cwd.
    project_root = project.expanduser().resolve() if project is not None else None
    lock_path = home_lock_path(home_root, lock_file=lock_file)
    surfaces = discover_host_surfaces(home=home_root)
    project_surfaces = (
        discover_project_surfaces(root=project_root) if project_root is not None else []
    )
    present = [s for s in surfaces if s.exists]
    present_project = [s for s in project_surfaces if s.exists]

    report: dict[str, Any] = {
        "schema_version": "watch-report/1",
        "home": str(home_root),
        "project": str(project_root) if project_root else None,
        "lock_path": str(lock_path),
        "lock_present": False,
        "surfaces": [
            {"host_id": surface.host_id, "path": str(surface.path)} for surface in present
        ],
        "project_surfaces": [
            {"host_id": surface.host_id, "path": str(surface.path)} for surface in present_project
        ],
        "surface_ids": _surface_ids([*present, *present_project]),
        "counts": dict.fromkeys(_REACH_KEYS, 0),
        "delta": {},
        "label": "NONE",
        "meaningful": False,
        "unparsed": 0,
        "empty": not present and not present_project,
        "first_run": False,
        "inventory_total": 0,
        "highlight_total": 0,
        "screen_digest": None,
        "error": None,
    }

    scan: ScanResult | None = None
    head: dict[str, Any] = dict(_EMPTY_LOCK)
    with ExitStack() as stack:
        synth, _staged = stage_watch_root(stack, home=home_root, project=project_root)
        scan = run_security_scan(synth)
        head = build_authority_lock(synth, scan=scan)

    head_records = list(head.get("records") or [])
    sealable = sealable_records(head_records)
    digest = screen_digest(sealable)
    report["counts"] = _counts(head_records)
    report["unparsed"] = _unparsed_count(scan)
    report["screen_digest"] = digest
    report["inventory_total"] = len(sealable)
    if project_root is not None and present_project:
        from auctelis.allow import project_is_allowed

        report["project_allow"] = project_is_allowed(project_root, home=home_root)

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
        # Show every sealable record (Project Trust: never hide what will be sealed).
        cards, highlight_total, inventory_total = highlight_cards(head_records)
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
            "changes": {"added": sealable, "removed": [], "changed": []},
        }
        return report, cards, scan

    delta = diff_authority_locks(base, head)
    summary = dict(delta.get("summary") or {})
    cards = delta_cards(delta, limit=6)
    meaningful = bool(cards or summary.get("policy_changed"))
    report["delta"] = delta
    report["label"] = delta_label(summary) if meaningful else "NONE"
    report["meaningful"] = meaningful
    return report, cards, scan


def seal_home_lock(
    *,
    home: Path | None = None,
    lock_file: Path | None = None,
    project: Path | None = None,
    accept: str | None = None,
) -> dict[str, Any]:
    """Seal the current host (+ project) authority. Human-only; never called by a hook.

    Requires ``accept`` to match the current screen digest so records never
    sealed were never shown.
    """
    home_root = (home or Path.home()).expanduser().resolve()
    project_root = project.expanduser().resolve() if project is not None else None
    lock_path = home_lock_path(home_root, lock_file=lock_file)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with ExitStack() as stack:
        synth, staged = stage_watch_root(stack, home=home_root, project=project_root)
        scan = run_security_scan(synth)
        head = build_authority_lock(synth, scan=scan)
        sealable = sealable_records(list(head.get("records") or []))
        digest = screen_digest(sealable)
        expected = str(accept or "").strip().lower()
        if not expected:
            raise ValueError(f"seal requires --accept {digest} (digest of every record on screen)")
        if expected != digest:
            raise ValueError(
                f"accept digest mismatch: got {expected!r}, screen is {digest!r} — "
                "re-run `auctelis watch` and pass the printed Accept digest"
            )
        if not staged:
            empty_tmp = stack.enter_context(
                tempfile.TemporaryDirectory(prefix="auctelis-empty-baseline-")
            )
            dest, lock = write_authority_lock(
                Path(empty_tmp),
                path=lock_path,
                accept_gated=True,
            )
            return {
                "path": str(dest),
                "records": len(lock.get("records") or []),
                "empty": True,
                "screen_digest": digest,
            }
        dest, lock = write_authority_lock(
            synth,
            path=lock_path,
            accept_gated=True,
            scan=scan,
        )
        return {
            "path": str(dest),
            "records": len(sealable),
            "empty": False,
            "screen_digest": digest,
        }


def why_home(
    query: str,
    *,
    home: Path | None = None,
    project: Path | None = None,
) -> tuple[list[str], int]:
    """Resolve ``auctelis why <name>`` against the current host inventory."""
    from auctelis.authority_card import find_records_by_name, why_record

    home_root = (home or Path.home()).expanduser().resolve()
    project_root = project.expanduser().resolve() if project is not None else None
    with ExitStack() as stack:
        synth, _staged = stage_watch_root(stack, home=home_root, project=project_root)
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
        f"{counts.get('skill', 0)} skills, {counts.get('host', 0)} host settings, "
        f"{counts.get('ci', 0)} CI"
    )


def _inventory_line(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    total = int(report.get("inventory_total") or 0)
    bits = []
    for key, label in (
        ("mcp", "MCP"),
        ("hook", "hooks"),
        ("skill", "skills"),
        ("host", "host settings"),
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

    digest = report.get("screen_digest")
    if digest and not report.get("lock_present"):
        lines.append(f"Accept digest: {digest}")

    if report.get("empty"):
        lines.append(f"No host config found under {report.get('home')}.")
        lines.append(_reach_line(counts))
        lines.append("")
        lines.append("Empty baseline: seal when you are ready, or add an agent host config.")
        if digest:
            lines.append(
                f"Next: `auctelis watch --seal --accept {digest}` "
                "(then `auctelis watch --arm` for session tripwires)."
            )
        else:
            lines.append(
                "Next: `auctelis watch --seal --accept <digest>` "
                "(then `auctelis watch --arm` for session tripwires)."
            )
        return "\n".join(lines)

    if surface_ids:
        lines.append(f"Found {len(surface_ids)} agent surface(s): {', '.join(surface_ids)}.")
    lines.append(_reach_line(counts))
    project_allow = report.get("project_allow")
    if isinstance(project_allow, dict):
        status = str(project_allow.get("status") or "unknown")
        if status == "allowed":
            lines.append(f"Project allow: allowed (digest {project_allow.get('digest')})")
        elif status == "drifted":
            lines.append(
                f"Project allow: DRIFTED (prior {project_allow.get('prior_digest')} → "
                f"{project_allow.get('digest')}) — run `auctelis allow --accept <digest>`"
            )
        else:
            lines.append(
                f"Project allow: not yet allowed (digest {project_allow.get('digest')}) — "
                "`auctelis allow --accept <digest>`"
            )
    lines.append("")

    if error:
        lines.append("Fix or remove the lock, then re-run `auctelis watch`.")
        return "\n".join(lines)

    current_cards = list(cards or [])

    if report.get("first_run"):
        highlight_total = int(report.get("highlight_total") or 0)
        inventory_total = int(report.get("inventory_total") or 0)
        if current_cards:
            lines.append("Authority on screen (every record that will be sealed):")
            lines.extend(current_cards)
            if inventory_total > len(current_cards):
                lines.append(f"… +{inventory_total - len(current_cards)} more records")
            elif highlight_total and highlight_total < inventory_total:
                pass
        else:
            lines.append("No sealable authority records detected.")
        lines.append(_inventory_line(report))
        lines.append("")
        unknown = "Unknown: publisher identity, effective permissions, runtime behavior."
        if int(report.get("unparsed") or 0):
            unknown += f" NOT PARSED: {report['unparsed']} agent config file(s)."
        lines.append(unknown)
        if digest:
            lines.append(
                f"Next: seal this baseline → `auctelis watch --seal --accept {digest}` "
                "(then `auctelis watch --arm`). Consent baseline, not a security clearance."
            )
        else:
            lines.append(
                "Next: seal this baseline → `auctelis watch --seal --accept <digest>` "
                "(then `auctelis watch --arm`). Consent baseline, not a security clearance."
            )
        return "\n".join(lines)

    if not report.get("meaningful"):
        lines.append("No authority change since you sealed.")
    else:
        lines.append("Delta since you sealed:")
        if digest:
            lines.append(f"Accept digest: {digest}")

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
        if digest:
            lines.append(
                f"Next: review, then `auctelis watch --seal --accept {digest}` "
                "to accept — or revert the config."
            )
        else:
            lines.append(
                "Next: review, then `auctelis watch --seal --accept <digest>` "
                "to accept — or revert the config."
            )
        lines.append("Tip: `auctelis why <name>` prints the exact config path.")
    else:
        lines.append("Next: nothing to do; the hook speaks only when authority changes.")
    return "\n".join(lines)
