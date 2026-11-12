"""authdiff command-line interface."""

from __future__ import annotations

from authdiff.cli.dispatch import dispatch
from authdiff.cli.parser import build_parser, normalize_argv


def main(argv: list[str] | None = None) -> int:
    """Product entry: bare → ``doctor`` (no repo config) or ``scan .``."""
    parser = build_parser(include_dev=False)
    args = parser.parse_args(normalize_argv(argv, include_dev=False))
    return dispatch(args)


def main_dev(argv: list[str] | None = None) -> int:
    """Maintainer entry point (`authdiff-dev`) with build/lint/corpus/…"""
    parser = build_parser(include_dev=True)
    args = parser.parse_args(argv)
    return dispatch(args)


__all__ = ["main", "main_dev", "normalize_argv"]
