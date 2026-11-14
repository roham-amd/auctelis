"""auctelis command-line interface."""

from __future__ import annotations

import contextlib
import sys

from auctelis.cli.dispatch import dispatch
from auctelis.cli.parser import build_parser, normalize_argv


def _ensure_utf8_stdout() -> None:
    """Authority cards use `→`; keep Windows consoles from crashing."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(OSError, ValueError):
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    """Product entry: bare → ``watch``; a path → hidden ``scan``."""
    _ensure_utf8_stdout()
    parser = build_parser(include_dev=False)
    args = parser.parse_args(normalize_argv(argv, include_dev=False))
    return dispatch(args)


def main_dev(argv: list[str] | None = None) -> int:
    """Maintainer entry point (`auctelis-dev`) with build/lint/corpus/…"""
    _ensure_utf8_stdout()
    parser = build_parser(include_dev=True)
    args = parser.parse_args(argv)
    return dispatch(args)


__all__ = ["main", "main_dev", "normalize_argv"]
