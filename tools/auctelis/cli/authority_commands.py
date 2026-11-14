"""CLI handlers for the Authority Watch first screen and host hooks."""

from __future__ import annotations

import argparse

from auctelis.cli.guards import refuse_agent_mutation
from auctelis.doctor import run_doctor
from auctelis.jsonio import print_json


def cmd_hook(args: argparse.Namespace) -> int:
    """Install or inspect Authority Watch hooks."""
    if getattr(args, "hook_command", None) == "status":
        from auctelis.hooks import hook_status, render_hook_status

        status = hook_status(
            home=getattr(args, "home", None),
            hooks_dir=getattr(args, "hooks_dir", None),
            settings_file=getattr(args, "settings_file", None),
            cursor_hooks_file=getattr(args, "cursor_hooks_file", None),
        )
        if getattr(args, "json", False):
            print_json(status)
        else:
            print(render_hook_status(status))
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

    home = getattr(args, "home", None)
    lock_file = getattr(args, "lock_file", None)
    report, cards, _scan = build_watch_report(home=home, lock_file=lock_file)

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
        sealed = seal_home_lock(home=home, lock_file=lock_file)
        print(
            f"Sealed {sealed['records']} authority record(s) → {sealed['path']} "
            "(human baseline; not a clearance)"
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
        )
        print_json(report)
        return code
    print(text)
    return code
