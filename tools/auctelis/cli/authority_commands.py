"""CLI handlers for repo check and why (product path)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from auctelis.jsonio import print_json

_ORG_REUSABLE_SLUG = re.compile(r"^[A-Za-z0-9_.-]+$")


def _note(message: str, *, as_json: bool) -> None:
    """Keep stdout machine-readable under ``--json``; human notes go to stderr."""
    print(message, file=sys.stderr if as_json else sys.stdout)


def _org_reusable_arg(args: argparse.Namespace) -> tuple[str | None, int | None]:
    """Validate ``--org-reusable`` (requires ``--report``; slug chars only).

    Returns ``(org_or_none, error_exit_code_or_none)``.
    """
    raw = getattr(args, "org_reusable", None)
    if raw is None:
        return None, None
    org = str(raw or "").strip().strip("/")
    if not org:
        print("auctelis check: --org-reusable requires a non-empty org slug.")
        return None, 2
    if not _ORG_REUSABLE_SLUG.fullmatch(org):
        print(f"auctelis check: --org-reusable must match [A-Za-z0-9_.-]+ (got {org!r}).")
        return None, 2
    if getattr(args, "report", None) is None:
        print("auctelis check: --org-reusable requires --report DIR.")
        return None, 2
    return org, None


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


def _load_baseline_arg(
    args: argparse.Namespace, *, expect_fleet: bool
) -> tuple[dict | None, int | None]:
    """Load and schema-check ``--baseline``. Returns ``(doc, error_exit)``."""
    baseline_path = getattr(args, "baseline", None)
    if baseline_path is None:
        return None, None
    from auctelis.export.reach_report import baseline_schema_mismatch, load_reach_baseline

    try:
        baseline = load_reach_baseline(baseline_path)
    except ValueError as exc:
        print(f"auctelis check: {exc}")
        return None, 2
    mismatch = baseline_schema_mismatch(baseline, expect_fleet=expect_fleet)
    if mismatch:
        print(f"auctelis check: {mismatch}")
        return None, 2
    return baseline, None


def _maybe_resolve_pins(args: argparse.Namespace, report: dict) -> None:
    if not getattr(args, "resolve_pins", False):
        return
    from auctelis.pin_resolve import resolve_pins_in_report

    resolve_pins_in_report(report)


def cmd_check(args: argparse.Namespace) -> int:
    """Repo-only authority vs AUTHORITY.lock (product front door)."""
    from auctelis.check import (
        build_check_report,
        check_exit_code,
        render_check,
        render_pin_report,
    )

    # Validate early so bad --org-reusable fails before any inventory work.
    _, org_err = _org_reusable_arg(args)
    if org_err is not None:
        return org_err

    if getattr(args, "resolve_pins", False) and not (
        getattr(args, "pins", False) or getattr(args, "report", None) is not None
    ):
        print("auctelis check: --resolve-pins requires --pins or --report.")
        return 2

    github_targets = getattr(args, "github", None)
    if github_targets:
        return _cmd_check_github(args, list(github_targets))

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
        strict_digests=bool(getattr(args, "strict_digests", False)),
    )
    _maybe_resolve_pins(args, report)
    report_dir = getattr(args, "report", None)
    as_json = bool(getattr(args, "json", False))
    if report_dir is not None:
        from auctelis.export.reach_report import write_reach_report_artifacts

        baseline, baseline_err = _load_baseline_arg(args, expect_fleet=False)
        if baseline_err is not None:
            return baseline_err
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
    if getattr(args, "pins", False):
        print("auctelis check: --pins applies to single-repo runs only.")
        return 2
    baseline, baseline_err = _load_baseline_arg(args, expect_fleet=True)
    if baseline_err is not None:
        return baseline_err
    top = int(getattr(args, "top", 5))
    limits = _collector_limits(args)
    entries: list[tuple[dict, ScanResult | None, list[str] | None]] = []
    codes: list[int] = []
    for root in paths:
        resolved = root.expanduser().resolve()
        if not resolved.is_dir():
            print(f"auctelis check: not a directory: {root}")
            return 2
        report, cards, scan = build_check_report(
            resolved,
            top=top,
            limits=limits,
            strict_digests=bool(getattr(args, "strict_digests", False)),
        )
        _maybe_resolve_pins(args, report)
        entries.append((report, scan, cards))
        codes.append(check_exit_code(report))
    org, _ = _org_reusable_arg(args)
    doc = write_fleet_reach_report_artifacts(
        report_dir,
        entries,
        org_reusable=org,
        baseline=baseline,
    )
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


def _cmd_check_github(args: argparse.Namespace, targets: list[str]) -> int:
    """Zero-clone GitHub org/repo fleet Reach Audit (AUCT-022/025)."""
    from auctelis.check import check_exit_code, render_check, render_pin_report
    from auctelis.export.reach_report import (
        render_fleet_summary,
        write_fleet_reach_report_artifacts,
        write_reach_report_artifacts,
    )
    from auctelis.github_audit import audit_github_repos

    cleaned = [str(t or "").strip().strip("/") for t in targets if str(t or "").strip()]
    report_dir = getattr(args, "report", None)
    # Single owner/repo may print to stdout; org / multi-repo require --report.
    needs_report = len(cleaned) != 1 or "/" not in cleaned[0]
    if report_dir is None and needs_report:
        print("auctelis check: --github requires --report DIR for org or multi-repo audits.")
        return 2
    if getattr(args, "lock_file", None) is not None:
        print("auctelis check: --lock-file does not apply with --github.")
        return 2
    if getattr(args, "path", None):
        paths = _paths(args)
        if paths != [Path(".")]:
            print("auctelis check: --github cannot be combined with local PATH arguments.")
            return 2

    top = int(getattr(args, "top", 5))
    max_repos = int(getattr(args, "max_repos", 50) or 50)
    include_forks = bool(getattr(args, "include_forks", False))
    as_json = bool(getattr(args, "json", False))
    # audit_github_repos never raises: failures become skipped rows + honesty notes.
    results, honesty = audit_github_repos(
        cleaned,
        max_repos=max_repos,
        top=top,
        limits=_collector_limits(args),
        include_forks=include_forks,
    )

    for note in honesty:
        _note(note, as_json=as_json)

    usable = [r for r in results if r.report is not None and not r.skipped]
    skipped_rows = [
        {
            "repository": r.repository,
            "notes": list(r.notes),
            "truncated": bool(r.truncated),
            "skipped": True,
        }
        for r in results
        if r.skipped
    ]
    if not usable:
        print("auctelis check: no repositories audited successfully.")
        return 2

    for row in usable:
        if row.report is not None:
            _maybe_resolve_pins(args, row.report)

    # Org / multi-target / any skipped row → fleet report so skipped_rows and
    # honesty notes stay visible (AUCT-027). Single owner/repo with no skips
    # keeps the compact single-repo path.
    use_fleet = bool(skipped_rows) or needs_report or len(usable) > 1

    if not use_fleet and len(usable) == 1 and not getattr(args, "pins", False):
        only = usable[0]
        assert only.report is not None
        baseline, baseline_err = _load_baseline_arg(args, expect_fleet=False)
        if baseline_err is not None:
            return baseline_err
        if report_dir is not None:
            write_reach_report_artifacts(
                report_dir,
                only.report,
                only.scan,
                cards=only.cards,
                baseline=baseline,
            )
            _note(f"Wrote reach report to {report_dir}", as_json=as_json)
        if as_json:
            doc = dict(only.report)
            if honesty:
                doc["honesty_notes"] = honesty
            if skipped_rows:
                doc["skipped"] = skipped_rows
            print_json(doc)
        else:
            print(render_check(only.report, only.cards))
        return check_exit_code(only.report)

    if getattr(args, "pins", False) and len(usable) == 1 and not use_fleet:
        only = usable[0]
        assert only.report is not None
        if report_dir is not None:
            baseline, baseline_err = _load_baseline_arg(args, expect_fleet=False)
            if baseline_err is not None:
                return baseline_err
            write_reach_report_artifacts(
                report_dir,
                only.report,
                only.scan,
                cards=only.cards,
                baseline=baseline,
            )
            _note(f"Wrote reach report to {report_dir}", as_json=as_json)
        print(render_pin_report(only.report))
        return check_exit_code(only.report)

    if getattr(args, "pins", False):
        print("auctelis check: --pins applies to single-repo --github owner/repo only.")
        return 2

    if report_dir is None:
        print("auctelis check: --github requires --report DIR for org or multi-repo audits.")
        return 2

    baseline, baseline_err = _load_baseline_arg(args, expect_fleet=True)
    if baseline_err is not None:
        return baseline_err

    entries = [(r.report, r.scan, r.cards) for r in usable if r.report is not None]
    org, _ = _org_reusable_arg(args)
    doc = write_fleet_reach_report_artifacts(
        report_dir,
        entries,
        skipped=skipped_rows,
        honesty_notes=honesty,
        org_reusable=org,
        baseline=baseline,
    )
    if as_json:
        print_json(doc)
    else:
        print(render_fleet_summary(doc))
    _note(
        f"Wrote fleet reach report to {report_dir} "
        "(reach-report.html / reach-report.md / reach-report.json)",
        as_json=as_json,
    )
    codes = [check_exit_code(r.report) for r in usable if r.report is not None]
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
