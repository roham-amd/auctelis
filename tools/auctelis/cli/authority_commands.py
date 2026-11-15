"""CLI handlers for repo check and why (product path)."""

from __future__ import annotations

import argparse

from auctelis.jsonio import print_json


def cmd_check(args: argparse.Namespace) -> int:
    """Repo-only authority vs AUTHORITY.lock (product front door)."""
    from auctelis.check import build_check_report, check_exit_code, render_check

    report, cards, _scan = build_check_report(
        getattr(args, "path", None),
        lock_file=getattr(args, "lock_file", None),
    )
    if getattr(args, "json", False):
        print_json(report)
    else:
        print(render_check(report, cards))
    return check_exit_code(report)


def cmd_why(args: argparse.Namespace) -> int:
    """Print exact config path / fields for one authority name."""
    from auctelis.check import why_repo

    lines, code = why_repo(
        str(getattr(args, "name", "") or ""),
        root=getattr(args, "path", None),
    )
    print("\n".join(lines).rstrip())
    return code
