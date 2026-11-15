"""Argparse construction for the auctelis CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# Single canonical public path — keep README / PRODUCT / INSTALL / ROADMAP in sync.
PUBLIC_PATH = "init --owner @team → check → lock --update → gate (PR Authority Diff)"

_EPILOG = f"""
public core:  {PUBLIC_PATH}
local:        status | diff --base <ref> | why <name> | demo
maintainer:   auctelis-dev (scan | annotate | build | lint | corpus | deps)

Bare `auctelis` → check (repo authority vs AUTHORITY.lock).
Labels: GROWTH | REDUCTION | NONE.
Verdicts: LOCKED | BASELINE_NEEDED | NEEDS_REVIEW | BASELINE_ADOPTED | FAIL_CLOSED.
Agents must set AUCTELIS_AGENT=1 and must not run lock / init / ci init
(AUCTELIS_AGENT is a speed bump, not a security control).
"""

# Hidden from default --help; still fully callable.
_ADV = argparse.SUPPRESS

# Enforceable public mental model — GitHub-native Authority Diff front door.
CORE_PUBLIC_COMMANDS = frozenset(
    {"check", "lock", "ci", "gate", "diff", "why", "demo", "init", "status"}
)

_PRODUCT_COMMANDS = frozenset(CORE_PUBLIC_COMMANDS)

_DEV_COMMANDS = frozenset(
    {
        "scan",
        "annotate",
        "build",
        "validate",
        "inventory",
        "verify",
        "export",
        "hosts",
        "corpus",
        "deps",
        "lint",
        # Kill-list: kept callable on auctelis-dev only; not product front door.
        "run",
        "snapshot",
        "artifact-vet",
    }
)


def normalize_argv(
    argv: Sequence[str] | None,
    *,
    include_dev: bool = False,
    cwd: Path | None = None,
) -> list[str]:
    """Default bare invocations to the repo authority check.

    ``auctelis`` → ``check`` (repo authority vs AUTHORITY.lock)
    ``auctelis /repo`` → ``check /repo``
    Known subcommands and ``-h`` / ``--help`` are left unchanged.

    ``cwd`` is accepted for call-site compatibility (reserved for path defaults).
    """
    _ = cwd
    raw = list(sys.argv[1:] if argv is None else argv)
    known = set(_PRODUCT_COMMANDS)
    if include_dev:
        known |= _DEV_COMMANDS
    if not raw:
        return ["check"]
    head = raw[0]
    if head in ("-h", "--help", "-V", "--version") or head in known:
        return raw
    if head.startswith("-"):
        return raw
    # Maintainer-only commands must not become ``check <cmd>`` on the product CLI.
    if not include_dev and head in (_DEV_COMMANDS - _PRODUCT_COMMANDS):
        return raw
    return ["check", *raw]


def build_parser(*, include_dev: bool = False) -> argparse.ArgumentParser:
    from auctelis.versioning import package_version, product_version

    prog = "auctelis-dev" if include_dev else "auctelis"
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Auctelis — the authority lockfile and PR review for what AI agents can reach. "
            "(Maintainer cmds: `auctelis-dev`)"
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {product_version()} (package {package_version()})",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    check = sub.add_parser(
        "check",
        help="Repo authority vs AUTHORITY.lock (front door; no host scan)",
    )
    check.add_argument("path", type=Path, nargs="?", default=Path("."))
    check.add_argument(
        "--lock-file",
        type=Path,
        help="AUTHORITY.lock path (default: <path>/AUTHORITY.lock)",
    )
    check.add_argument(
        "--json",
        action="store_true",
        help="Emit authority-diff/1 JSON",
    )

    init_cmd = sub.add_parser(
        "init",
        help="One-command setup: policy + workflow + CODEOWNERS + lock (preferred)",
    )
    init_cmd.add_argument("path", type=Path, nargs="?", default=Path("."))
    init_cmd.add_argument("--force", action="store_true")
    init_cmd.add_argument(
        "--owner",
        metavar="@TEAM",
        required=True,
        help="CODEOWNERS identity for AUTHORITY.lock (e.g. @security-owners)",
    )
    init_cmd.add_argument(
        "--advisory",
        action="store_true",
        help="Write advisory mode (locked=false); default is enforce",
    )
    init_cmd.add_argument(
        "--accept-gated",
        action="store_true",
        help="Allow sealing when a findings-bearing scan is passed (usually unused)",
    )

    status_cmd = sub.add_parser(
        "status",
        help="Show lock / workflow / CODEOWNERS / protection status",
    )
    status_cmd.add_argument("path", type=Path, nargs="?", default=Path("."))

    ci = sub.add_parser("ci", help="Write enforce workflow + CODEOWNERS + lock")
    ci_sub = ci.add_subparsers(dest="ci_command", required=True)
    ci_init = ci_sub.add_parser(
        "init",
        help="Write .auctelis.yml + enforce workflow + CODEOWNERS + AUTHORITY.lock",
    )
    ci_init.add_argument("path", type=Path, nargs="?", default=Path("."))
    ci_init.add_argument("--force", action="store_true")
    ci_init.add_argument(
        "--owner",
        metavar="@TEAM",
        help="CODEOWNERS identity for AUTHORITY.lock (e.g. @security-owners); required",
    )
    ci_init.add_argument(
        "--advisory",
        action="store_true",
        help="Write advisory mode (locked=false); default is enforce",
    )
    ci_init.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Merge AUTHORITY.lock into existing CODEOWNERS, pin the Action to "
            "the auctelis release tag (never consumer HEAD), and probe ruleset/"
            "branch-protection (warnings only; exit 0 after writes)"
        ),
    )
    ci_init.add_argument(
        "--accept-gated",
        action="store_true",
        help="Allow sealing when a findings-bearing scan blocks the lock write",
    )
    ci_init.set_defaults(command="ci")

    why = sub.add_parser(
        "why",
        help="Show the exact config path for one authority name",
    )
    why.add_argument("name", help="Authority record name (MCP server, skill, hook, …)")
    why.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Repository root (default: cwd)",
    )

    demo = sub.add_parser(
        "demo",
        help="Optional packaged fixture: scan demo-vulnerable and print the Authority Diff",
    )
    demo.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory (default: ./auctelis-out-demo)",
    )
    demo.add_argument(
        "--fail-on",
        choices=["never", "high", "any"],
        default="never",
        help="Ignored for exit code (demo always exits 0); kept for compatibility",
    )

    lock_cmd = sub.add_parser(
        "lock",
        help="Write or verify AUTHORITY.lock (record-level agent authority)",
    )
    lock_cmd.add_argument("path", type=Path, nargs="?", default=Path("."))
    lock_cmd.add_argument(
        "--check",
        action="store_true",
        help="Regenerate and compare to the committed lock (exit 1 on drift)",
    )
    lock_cmd.add_argument(
        "--update",
        action="store_true",
        help="Rewrite AUTHORITY.lock from the current tree",
    )
    lock_cmd.add_argument(
        "--lock-file",
        type=Path,
        help="Lock destination/path (default: <path>/AUTHORITY.lock)",
    )
    lock_cmd.add_argument(
        "--approval",
        metavar="OWNER",
        help=(
            "Deprecated no-op. CODEOWNERS + rulesets are the approval system; "
            "no approval fields are written."
        ),
    )
    lock_cmd.add_argument(
        "--accept-gated",
        action="store_true",
        help=(
            "Allow writing a lock when the tree has HIGH/CRITICAL gated findings. "
            "Use for intentional baseline seals; prefer remediating first."
        ),
    )
    lock_cmd.add_argument(
        "--snapshot",
        type=Path,
        help=argparse.SUPPRESS,  # opt-in broker pin path — not product
    )
    lock_cmd.add_argument(
        "--resolve",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    gate_cmd = sub.add_parser(
        "gate",
        help="PR Authority Diff: base lock → head (CODEOWNERS / ruleset gate)",
    )
    gate_cmd.add_argument("path", type=Path, nargs="?", default=Path("."))
    gate_cmd.add_argument(
        "--base-lock",
        type=Path,
        required=True,
        help="Approved AUTHORITY.lock from the PR base ref (or prior release)",
    )
    gate_cmd.add_argument(
        "--head-lock",
        type=Path,
        help="Head AUTHORITY.lock (default: regenerate from the scan target)",
    )
    gate_cmd.add_argument(
        "--codeowners",
        type=Path,
        help="Trusted CODEOWNERS file (prefer base-ref copy in CI)",
    )
    gate_cmd.add_argument(
        "--skip-ruleset-check",
        action="store_true",
        help="Skip best-effort GitHub ruleset/branch-protection probe",
    )
    gate_cmd.add_argument(
        "--strict-ruleset",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Fail growth when ruleset status is UNVERIFIED "
            "(default: on; use --no-strict-ruleset for best-effort)"
        ),
    )
    gate_cmd.add_argument(
        "--trust-head-codeowners",
        action="store_true",
        help=(
            "Unsafe: accept CODEOWNERS from the head tree when no base-ref "
            "copy was supplied (default: require --codeowners from base)"
        ),
    )
    gate_cmd.add_argument(
        "--agent",
        action="store_true",
        help="Emit JSON gate report",
    )

    if include_dev:
        _add_dev_commands(sub)

    diff_parser = sub.add_parser(
        "diff",
        help="Local PR Authority Diff simulator (`--base <ref>` or `lock`)",
    )
    diff_parser.add_argument(
        "--base",
        metavar="REF",
        help="Git ref whose AUTHORITY.lock is the approved base (git show)",
    )
    diff_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Repository root for --base mode (default: .)",
    )
    diff_parser.add_argument(
        "--json",
        action="store_true",
        dest="diff_json",
        help="Emit JSON (authority-diff/1 + comment body)",
    )
    diff_sub = diff_parser.add_subparsers(dest="diff_kind", required=False)
    diff_lock = diff_sub.add_parser(
        "lock",
        help="Diff two AUTHORITY.lock files (record-level authority)",
    )
    diff_lock.add_argument("base", type=Path)
    diff_lock.add_argument("head", type=Path)
    diff_lock.add_argument(
        "--agent",
        action="store_true",
        help="Emit JSON instead of line-oriented text",
    )

    # argparse still registers help=SUPPRESS choices; drop them from --help listing.
    sub._choices_actions = [a for a in sub._choices_actions if a.help != _ADV]

    return parser


def _add_dev_commands(sub: Any) -> None:
    """Maintainer commands — only on ``auctelis-dev`` (research surface removed)."""
    _add_scan_parser(sub)
    _add_annotate_parser(sub)

    build = sub.add_parser("build", help="Run build and consistency checks")
    build.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "schemas"],
        help="Build target (default: all)",
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
        "command",
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


def _add_scan_parser(sub: Any) -> None:
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


def _add_annotate_parser(sub: Any) -> None:
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
