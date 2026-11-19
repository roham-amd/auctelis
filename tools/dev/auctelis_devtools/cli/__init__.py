"""``auctelis-dev`` entry: product parser + maintainer commands."""

from __future__ import annotations

import argparse
import contextlib
import sys

from auctelis.cli.dispatch import dispatch as product_dispatch
from auctelis.cli.parser import _DEV_COMMANDS, build_parser, normalize_argv
from auctelis_devtools.cli.dev_commands import (
    cmd_annotate,
    cmd_artifact_vet,
    cmd_build,
    cmd_corpus,
    cmd_deps,
    cmd_export,
    cmd_hosts,
    cmd_inventory,
    cmd_lint,
    cmd_run,
    cmd_scan,
    cmd_snapshot,
    cmd_validate,
    cmd_verify,
)


def _ensure_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(OSError, ValueError):
            reconfigure(encoding="utf-8", errors="replace")


def dispatch_dev(args: argparse.Namespace) -> int:
    """Route maintainer commands; fall through to the product dispatcher."""
    command = args.command
    if command == "ci":
        return product_dispatch(args)
    if command not in _DEV_COMMANDS:
        return product_dispatch(args)
    match command:
        case "scan":
            return cmd_scan(args)
        case "annotate":
            return cmd_annotate(args)
        case "build":
            return cmd_build(args)
        case "validate":
            return cmd_validate(args)
        case "inventory":
            return cmd_inventory(args)
        case "verify":
            return cmd_verify(args)
        case "export":
            return cmd_export(args)
        case "hosts":
            return cmd_hosts(args)
        case "corpus":
            return cmd_corpus()
        case "deps":
            return cmd_deps(args)
        case "lint":
            return cmd_lint(args)
        case "run":
            return cmd_run(args)
        case "snapshot":
            return cmd_snapshot(args)
        case "artifact-vet":
            return cmd_artifact_vet(args)
        case _:
            return 2


def main_dev(argv: list[str] | None = None) -> int:
    """Maintainer entry point (`auctelis-dev`) with build/lint/corpus/…"""
    _ensure_utf8_stdout()
    parser = build_parser(include_dev=True)
    args = parser.parse_args(normalize_argv(argv, include_dev=True))
    return dispatch_dev(args)


__all__ = ["dispatch_dev", "main_dev"]
