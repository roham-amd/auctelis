"""CLI handlers for repo check and why (product path)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from auctelis.jsonio import print_json


def _note(message: str, *, as_json: bool) -> None:
    """Keep stdout machine-readable under ``--json``; human notes go to stderr."""
    print(message, file=sys.stderr if as_json else sys.stdout)


def _paths(args: argparse.Namespace) -> list[Path]:
    """Normalize ``check [PATH ...]`` (zero paths means the current directory)."""
    raw = getattr(args, "path", None)
    if isinstance(raw, list):
        return [Path(p) for p in raw] or [Path(".")]
    if raw is None:
        return [Path(".")]
    return [Path(raw)]


def _collector_limits(args: argparse.Namespace) -> object | None:
    max_files = getattr(args, "max_files", None)
    if max_files is None:
        return None
    from auctelis.inventory.limits import resolve_collector_limits

    return resolve_collector_limits(max_files=max_files)


def cmd_check(args: argparse.Namespace) -> int:
    """Repo-only authority vs AUTHORITY.lock (product front door)."""
    from auctelis.check import (
        build_check_report,
        check_exit_code,
        render_check,
        render_pin_report,
    )

    paths = _paths(args)
    if len(paths) > 1:
        return _cmd_check_fleet(args, paths)
    root = paths[0].expanduser().resolve()
    if not root.is_dir():
        print(f"auctelis check: not a directory: {paths[0]}")
        return 2
    top = int(getattr(args, "top", 5))
    report, cards, scan = build_check_report(
        root,
        lock_file=getattr(args, "lock_file", None),
        top=top,
        limits=_collector_limits(args),
    )
    report_dir = getattr(args, "report", None)
    as_json = bool(getattr(args, "json", False))
    if report_dir is not None:
        from auctelis.export.reach_report import (
            load_reach_baseline,
            write_reach_report_artifacts,
        )

        baseline_path = getattr(args, "baseline", None)
        baseline = None
        if baseline_path is not None:
            try:
                baseline = load_reach_baseline(baseline_path)
            except ValueError as exc:
                print(f"auctelis check: {exc}")
                return 2
        write_reach_report_artifacts(
            report_dir,
            report,
            scan,
            cards=cards,
            baseline=baseline,
        )
        _note(f"Wrote reach report to {report_dir}", as_json=as_json)
    if getattr(args, "json", False):
        print_json(report)
    elif getattr(args, "pins", False):
        print(render_pin_report(report))
    else:
        print(render_check(report, cards))
    return check_exit_code(report)


def _cmd_check_fleet(args: argparse.Namespace, paths: list[Path]) -> int:
    """Audit several repositories into one shareable fleet reach report."""
    from auctelis.check import build_check_report, check_exit_code
    from auctelis.export.reach_report import (
        render_fleet_summary,
        write_fleet_reach_report_artifacts,
    )
    from auctelis.security.engine import ScanResult

    report_dir = getattr(args, "report", None)
    if report_dir is None:
        print("auctelis check: multiple paths require --report DIR (fleet reach report).")
        return 2
    if getattr(args, "lock_file", None) is not None:
        print("auctelis check: --lock-file applies to single-repo runs only.")
        return 2
    if getattr(args, "baseline", None) is not None:
        print("auctelis check: --baseline applies to single-repo runs only.")
        return 2
    if getattr(args, "pins", False):
        print("auctelis check: --pins applies to single-repo runs only.")
        return 2
    top = int(getattr(args, "top", 5))
    limits = _collector_limits(args)
    entries: list[tuple[dict, ScanResult | None, list[str] | None]] = []
    codes: list[int] = []
    for root in paths:
        resolved = root.expanduser().resolve()
        if not resolved.is_dir():
            print(f"auctelis check: not a directory: {root}")
            return 2
        report, cards, scan = build_check_report(resolved, top=top, limits=limits)
        entries.append((report, scan, cards))
        codes.append(check_exit_code(report))
    doc = write_fleet_reach_report_artifacts(report_dir, entries)
    as_json = bool(getattr(args, "json", False))
    if as_json:
        print_json(doc)
    else:
        print(render_fleet_summary(doc))
    _note(
        f"Wrote fleet reach report to {report_dir} "
        "(reach-report.html / reach-report.md / reach-report.json)",
        as_json=as_json,
    )
    if any(code == 2 for code in codes):
        return 2
    return 1 if any(code == 1 for code in codes) else 0


def cmd_why(args: argparse.Namespace) -> int:
    """Print exact config path / fields for one authority name."""
    from auctelis.check import why_repo

    lines, code = why_repo(
        str(getattr(args, "name", "") or ""),
        root=getattr(args, "path", None),
    )
    print("\n".join(lines).rstrip())
    return code
