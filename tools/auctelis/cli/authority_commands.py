"""CLI handlers for repo check, archived watch/allow/hooks, and why."""

from __future__ import annotations

import argparse

from auctelis.cli.guards import refuse_agent_mutation
from auctelis.doctor import run_doctor
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
    """Print exact config path / fields for one authority name (repo-first)."""
    from auctelis.check import why_repo

    # Archived host why when --home is explicitly passed.
    if getattr(args, "home", None) is not None:
        from auctelis.watch import why_home

        lines, code = why_home(
            str(getattr(args, "name", "") or ""),
            home=getattr(args, "home", None),
            project=getattr(args, "path", None),
        )
    else:
        lines, code = why_repo(
            str(getattr(args, "name", "") or ""),
            root=getattr(args, "path", None),
        )
    print("\n".join(lines).rstrip())
    return code


def cmd_allow(args: argparse.Namespace) -> int:
    """Allow (or inspect) the current project's authority hash."""
    from auctelis.allow import allow_project, project_is_allowed

    root = getattr(args, "path", None)
    home = getattr(args, "home", None)
    if getattr(args, "status", False):
        status = project_is_allowed(root, home=home)
        if getattr(args, "json", False):
            print_json(status)
        else:
            print(
                f"auctelis allow: {status.get('status')} · digest {status.get('digest')} · "
                f"{status.get('record_count', 0)} record(s)"
            )
            if status.get("status") == "drifted":
                print(f"  prior: {status.get('prior_digest')} → re-run `auctelis allow`")
            elif status.get("status") == "unknown":
                print("  Next: review project authority, then `auctelis allow`")
        return 0 if status.get("allowed") else 1
    refused = refuse_agent_mutation("allow")
    if refused is not None:
        return refused
    try:
        entry = allow_project(
            root,
            home=home,
            accept=getattr(args, "accept", None),
        )
    except ValueError as exc:
        print(f"auctelis allow: {exc}", file=__import__("sys").stderr)
        return 2
    if getattr(args, "json", False):
        print_json(entry)
    else:
        print(
            f"Allowed project {entry['path']} · digest {entry['digest']} · "
            f"{entry['record_count']} record(s)"
        )
    return 0


def cmd_hook(args: argparse.Namespace) -> int:
    """Install or inspect Authority Watch hooks."""
    if getattr(args, "hook_command", None) == "status":
        from auctelis.hooks import hook_status, probe_hooks, render_hook_status

        status = hook_status(
            home=getattr(args, "home", None),
            hooks_dir=getattr(args, "hooks_dir", None),
            settings_file=getattr(args, "settings_file", None),
            cursor_hooks_file=getattr(args, "cursor_hooks_file", None),
        )
        if getattr(args, "probe", False):
            status["probe"] = probe_hooks(
                home=getattr(args, "home", None),
                hooks_dir=getattr(args, "hooks_dir", None),
            )
        if getattr(args, "json", False):
            print_json(status)
        else:
            print(render_hook_status(status))
        if getattr(args, "probe", False) and not (status.get("probe") or {}).get("passed"):
            return 1
        return 0
    if getattr(args, "hook_command", None) != "install":
        return 2
    refused = refuse_agent_mutation("hook install")
    if refused is not None:
        return refused
    from auctelis.hooks import install_hooks

    session_only = bool(getattr(args, "session_only", False))
    pretool_only = bool(getattr(args, "pretool_only", False))
    wire = not bool(getattr(args, "no_wire", False))
    result = install_hooks(
        home=getattr(args, "home", None),
        hooks_dir=getattr(args, "hooks_dir", None),
        session=not pretool_only,
        pretool=not session_only,
        wire_claude=wire,
        wire_cursor=wire and not bool(getattr(args, "no_cursor", False)),
    )
    for message in result.get("messages") or []:
        print(message)
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """One-screen declared authority delta; optional seal and hook arming."""
    from auctelis.watch import build_watch_report, render_watch, seal_home_lock

    seal = bool(getattr(args, "seal", False))
    arm = bool(getattr(args, "arm", False))
    if seal or arm:
        refused = refuse_agent_mutation("watch --seal/--arm")
        if refused is not None:
            return refused

    from pathlib import Path

    home = getattr(args, "home", None)
    lock_file = getattr(args, "lock_file", None)
    # CLI defaults project to cwd so cloning a repo is on the product path.
    project = getattr(args, "project", None) or Path.cwd()
    report, cards, _scan = build_watch_report(home=home, lock_file=lock_file, project=project)

    if getattr(args, "json", False):
        print_json(report)
    else:
        print(
            render_watch(
                report,
                cards,
                delta_only=bool(getattr(args, "delta_only", False)),
            )
        )

    code = 2 if report.get("error") else (1 if report.get("meaningful") else 0)
    if getattr(args, "delta_only", False) and not report.get("lock_present"):
        code = 0
    if seal:
        try:
            sealed = seal_home_lock(
                home=home,
                lock_file=lock_file,
                project=project,
                accept=getattr(args, "accept", None),
            )
        except ValueError as exc:
            print(f"auctelis watch --seal: {exc}", file=__import__("sys").stderr)
            return 2
        print(
            f"Sealed {sealed['records']} authority record(s) → {sealed['path']} "
            f"(digest {sealed.get('screen_digest')}; human baseline; not a clearance)"
        )
        code = 0
    if arm:
        from auctelis.hooks import install_hooks

        result = install_hooks(home=home)
        for message in result.get("messages") or []:
            print(message)
    return code


def cmd_doctor(args: argparse.Namespace) -> int:
    """Alias for watch with optional compact agent JSON."""
    text, code = run_doctor(
        home=getattr(args, "home", None),
        output_dir=getattr(args, "output_dir", None),
        fail_on=getattr(args, "fail_on", None),
        since_lock=bool(getattr(args, "since_lock", False)),
        lock_file=getattr(args, "lock_file", None),
        delta_only=bool(getattr(args, "delta_only", False)),
    )
    if getattr(args, "agent", False):
        from auctelis.watch import build_watch_report

        report, _cards, _scan = build_watch_report(
            home=getattr(args, "home", None),
            lock_file=getattr(args, "lock_file", None),
            project=getattr(args, "project", None),
        )
        print_json(report)
        return code
    print(text)
    return code
