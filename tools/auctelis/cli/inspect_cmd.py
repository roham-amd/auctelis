"""CLI handler for ``auctelis inspect`` (Trust Dossier)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from auctelis.export.dossier import render_dossier_markdown, render_dossier_text
from auctelis.github_audit import GitHubAuditError
from auctelis.inspect_target import inspect_target
from auctelis.jsonio import print_json, write_json, write_text
from auctelis.local_hosts import inspect_local_hosts


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect a target and print or write a Trust Dossier."""
    if args.local and args.target is not None:
        print(
            "auctelis inspect: --local cannot be combined with TARGET.",
            file=sys.stderr,
        )
        return 2
    if args.home is not None and not args.local:
        print("auctelis inspect: --home requires --local.", file=sys.stderr)
        return 2

    try:
        if args.local:
            doc = inspect_local_hosts(home=args.home, offline=args.offline)
        else:
            doc = inspect_target(
                args.target if args.target is not None else ".",
                offline=args.offline,
            )
    except (ValueError, OSError, GitHubAuditError) as exc:
        print(f"auctelis inspect: {exc}", file=sys.stderr)
        return 2

    out = getattr(args, "out", None)
    if out:
        out_dir = Path(out)
        write_json(out_dir / "dossier.json", doc)
        write_text(out_dir / "dossier.md", render_dossier_markdown(doc))

    if getattr(args, "json", False):
        print_json(doc)
    elif getattr(args, "markdown", False):
        print(render_dossier_markdown(doc))
    else:
        print(render_dossier_text(doc))

    return 0 if doc.get("verdict") == "UNVERIFIED_CLEAN" else 1
