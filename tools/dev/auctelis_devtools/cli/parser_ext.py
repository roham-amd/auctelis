"""Maintainer argparse extensions for ``auctelis-dev``."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def add_dev_commands(sub: Any) -> None:
    """Maintainer commands — only on ``auctelis-dev`` (research surface removed)."""
    add_scan_parser(sub)
    add_annotate_parser(sub)

    build = sub.add_parser("build", help="Run build and consistency checks")
    build.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "schemas", "pypi-check"],
        help="Build target (default: all; pypi-check = cutover readiness)",
    )
    build.add_argument(
        "--live",
        action="store_true",
        help="With pypi-check: query PyPI JSON for this VERSION (HTTP status)",
    )

    val = sub.add_parser("validate", help="Validate auctelis JSON artifacts")
    val_sub = val.add_subparsers(dest="validate_cmd", required=True)
    rep = val_sub.add_parser("report", help="Validate findings/report JSON")
    rep.add_argument("path", type=Path)
    rep.add_argument("--no-semantic", action="store_true")

    inv = sub.add_parser("inventory", help="Passive read-only inventory of a directory")
    inv.add_argument("path", type=Path)
    inv.add_argument("-o", "--output", type=Path, help="Write JSON to file")

    verify = sub.add_parser("verify", help="Supply-chain verification helpers")
    verify_sub = verify.add_subparsers(dest="verify_cmd", required=True)
    digest = verify_sub.add_parser("digest", help="Compute or verify SHA-256 of a file")
    digest.add_argument("path", type=Path)
    digest.add_argument("--expected", help="Expected sha256 hex digest")

    export = sub.add_parser("export", help="Export interoperable formats")
    export_sub = export.add_subparsers(dest="export_cmd", required=True)
    sarif_cmd = export_sub.add_parser("sarif", help="Export SARIF 2.1.0")
    sarif_cmd.add_argument("report", type=Path)
    sarif_cmd.add_argument("-o", "--output", type=Path)

    hosts = sub.add_parser("hosts", help="List or show agent-host profiles")
    hosts_sub = hosts.add_subparsers(dest="hosts_cmd", required=True)
    hosts_sub.add_parser("list")
    hosts_show = hosts_sub.add_parser("show")
    hosts_show.add_argument("host_id")

    corp = sub.add_parser("corpus", help="Security regression corpus harness")
    corp_sub = corp.add_subparsers(dest="corpus_cmd", required=True)
    corp_sub.add_parser("run")

    deps = sub.add_parser("deps", help="Check/upgrade dependencies")
    deps_sub = deps.add_subparsers(dest="deps_cmd", required=True)
    deps_sub.add_parser("outdated")
    dep_up = deps_sub.add_parser("upgrade")
    dep_up.add_argument("--dry-run", action="store_true")

    lint = sub.add_parser("lint", help="Run Ruff on tools + tests")
    lint.add_argument("--fix", action="store_true")
    lint.add_argument("--format", action="store_true", dest="format_code")
    lint.add_argument("--check-format", action="store_true")

    run_cmd = sub.add_parser("run", help="Env-scrub launcher (NOT a sandbox)")
    run_cmd.add_argument(
        "--lock",
        type=Path,
        help="Optional AUTHORITY.lock / AUTHORITY.lock.json",
    )
    run_cmd.add_argument(
        "run_command",
        nargs=argparse.REMAINDER,
        help="Command after -- , e.g. auctelis-dev run -- npx -y server",
    )

    snap = sub.add_parser("snapshot", help="tools/list snapshot helper")
    snap.add_argument(
        "--from-file",
        type=Path,
        help="Read a tools/list JSON payload from disk (no execute)",
    )
    snap.add_argument(
        "--execute",
        nargs=argparse.REMAINDER,
        help="Opt-in: run command after -- expecting JSON tools/list on stdout",
    )
    snap.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow network in execute mode (still scrubbed env)",
    )
    snap.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write snapshot JSON",
    )

    art = sub.add_parser("artifact-vet", help="Heuristic package artifact annotations")
    art.add_argument(
        "spec",
        help="npm:name[@ver] | pypi:name[==ver] | bare name (heuristic)",
    )
    art.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write artifact report JSON",
    )


def add_scan_parser(sub: Any) -> None:
    """Hidden scanner — CI / maintainer only (``auctelis-dev scan``)."""
    scan = sub.add_parser(
        "scan",
        help="Passive repo scan for findings (maintainer / GitHub Action)",
    )
    scan.add_argument("path", type=Path, nargs="?", default=Path("."))
    scan.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory (default: ./auctelis-out in the current working directory)",
    )
    scan.add_argument(
        "--baseline",
        type=Path,
        help="Prior baseline.json for risk delta",
    )
    scan.add_argument(
        "--save-baseline",
        type=Path,
        help="Write baseline.json after scan",
    )
    scan.add_argument(
        "--fail-on",
        choices=["never", "high", "any"],
        default=None,
        help="Exit non-zero when findings match policy (default: never, or .auctelis.yml)",
    )
    scan.add_argument(
        "--policy",
        type=Path,
        help="Path to .auctelis.yml (default: only inside the scan target tree)",
    )
    scan.add_argument(
        "--no-policy",
        action="store_true",
        help="Ignore .auctelis.yml even if present",
    )
    scan.add_argument(
        "--trust-target-policy",
        action="store_true",
        help=(
            "Load <target>/.auctelis.yml (including suppressions). "
            "Default is to ignore target policy so audited repos cannot blind the scanner."
        ),
    )
    scan.add_argument(
        "--locked",
        action="store_true",
        help="Fail when observed authority drifts from committed AUTHORITY.lock",
    )
    scan.add_argument(
        "--lock-file",
        type=Path,
        help="AUTHORITY.lock path for --locked (default: <target>/AUTHORITY.lock)",
    )
    scan.add_argument(
        "--base-lock",
        type=Path,
        help=(
            "Approved AUTHORITY.lock (typically from the PR base ref). "
            "Diffed against observed head authority (advisory; gate is the verdict)."
        ),
    )
    scan.add_argument(
        "--include-fixtures",
        action="store_true",
        help="Include tests/examples/docs/fixtures dirs (excluded by default)",
    )
    scan.add_argument(
        "--full",
        action="store_true",
        help="Print the long terminal report (default is ≤15 lines)",
    )
    scan.add_argument(
        "--agent",
        action="store_true",
        help="Emit compact agent JSON digest (fenced evidence; token-bounded)",
    )


def add_annotate_parser(sub: Any) -> None:
    """Findings annotations — CI only (``auctelis-dev annotate``)."""
    annotate = sub.add_parser(
        "annotate",
        help="Emit GitHub / PR-comment annotations from findings.json",
    )
    annotate.add_argument(
        "findings",
        type=Path,
        nargs="?",
        default=Path("auctelis-out/findings.json"),
        help="Path to findings.json (default: auctelis-out/findings.json)",
    )
    annotate.add_argument(
        "--format",
        choices=["github", "text", "pr-comment"],
        default="github",
        dest="annotate_format",
        help="Annotation format (default: github; pr-comment = ≤12-line Authority Diff)",
    )
    annotate.add_argument(
        "--risk-delta",
        type=Path,
        help="Optional risk-delta.json for delta-first PR comments",
    )
