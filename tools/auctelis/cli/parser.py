"""Argparse construction for the auctelis CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

# Single canonical public path — keep README / PRODUCT / INSTALL / ROADMAP in sync.
PUBLIC_PATH = "check → check --report / --github → rollout → init --lockless → gate"

_EPILOG = f"""
first path:   {PUBLIC_PATH}
local:        status [--check] | why <name> | demo
maintainer:   auctelis-dev (source checkout; research not in the wheel)

Bare `auctelis` → check (tree-truth reach; AUTHORITY.lock optional).
Labels: GROWTH | REDUCTION | NONE.
Verdicts: LOCKED | BASELINE_NEEDED | NEEDS_REVIEW | BASELINE_ADOPTED | FAIL_CLOSED | PASS.
Agents must set AUCTELIS_AGENT=1 and must not run lock / init / rollout --apply
(AUCTELIS_AGENT is a speed bump, not a security control).
"""

# Enforceable public mental model — GitHub-native Authority Diff front door.
CORE_PUBLIC_COMMANDS = frozenset(
    {
        "check",
        "lock",
        "ci",
        "gate",
        "diff",
        "why",
        "demo",
        "init",
        "status",
        "trust",
        "rollout",
    }
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
        help="Tree-truth reach report (lock optional; --github for zero-clone org audit)",
    )
    check.add_argument(
        "path",
        type=Path,
        nargs="*",
        default=None,
        metavar="PATH",
        help="Repository root(s); more than one path requires --report (fleet report)",
    )
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
    check.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Show the top N reach cards (default: 5; 0 hides cards)",
    )
    check.add_argument(
        "--pins",
        action="store_true",
        help="Show unpinned/floating MCP servers with concrete pin fixes",
    )
    check.add_argument(
        "--resolve-pins",
        action="store_true",
        help=(
            "With --pins or --report: look up exact npm/PyPI latest versions "
            "(opt-in; trust-on-first-use; Docker digests stay placeholders)"
        ),
    )
    check.add_argument(
        "--report",
        type=Path,
        metavar="DIR",
        help="Write shareable reach report (HTML+MD+JSON+SBOM) under DIR",
    )
    check.add_argument(
        "--baseline",
        type=Path,
        metavar="PATH",
        help=(
            "Prior reach-report.json (or check --json / fleet report) to diff "
            "against when using --report (single-repo, fleet, or --github)"
        ),
    )
    check.add_argument(
        "--max-files",
        type=int,
        default=None,
        metavar="N",
        help="Inventory walk file cap (default: 50000 or AUCTELIS_MAX_FILES)",
    )
    check.add_argument(
        "--github",
        nargs="+",
        metavar="TARGET",
        help=(
            "Zero-clone GitHub audit: org name and/or owner/repo slugs "
            "(--report required for org/multi-repo; single owner/repo may omit it; "
            "uses GITHUB_TOKEN/GH_TOKEN or gh auth token)"
        ),
    )
    check.add_argument(
        "--max-repos",
        type=int,
        default=50,
        metavar="N",
        help="Cap repositories when --github lists an org (default: 50)",
    )
    check.add_argument(
        "--include-forks",
        action="store_true",
        help="Include forked repositories when --github lists an org (default: skip forks)",
    )
    check.add_argument(
        "--strict-digests",
        action="store_true",
        help=(
            "Fail on plain-CI / prose representation digest drift "
            "(default: advisory only; Hook body edits always fail)"
        ),
    )
    check.add_argument(
        "--org-reusable",
        metavar="ORG",
        help=(
            "With --report, record ORG so rollout installs the org-reusable caller "
            "(ORG/.github/.../auctelis-org-reusable.yml@main)"
        ),
    )

    init_cmd = sub.add_parser(
        "init",
        help="One-command setup: lockless workflow, or policy + CODEOWNERS + lock",
    )
    init_cmd.add_argument("path", type=Path, nargs="?", default=Path("."))
    init_cmd.add_argument("--force", action="store_true")
    init_cmd.add_argument(
        "--lockless",
        action="store_true",
        help=(
            "Write only .github/workflows/auctelis.yml (comment-only PR Watch; "
            "no lock, policy, or CODEOWNERS; --owner not required)"
        ),
    )
    init_cmd.add_argument(
        "--owner",
        metavar="TEAM",
        required=False,
        help=(
            "CODEOWNERS identity for AUTHORITY.lock (e.g. security; @ optional); "
            "required unless --lockless"
        ),
    )
    init_cmd.add_argument(
        "--enforce",
        action="store_true",
        help="Opt into enforce mode (locked=true + strict ruleset); default is comment-only",
    )
    init_cmd.add_argument(
        "--advisory",
        action="store_true",
        help="Comment-only mode (default; locked=false)",
    )
    init_cmd.add_argument(
        "--accept-gated",
        action="store_true",
        help="Allow sealing when a findings-bearing scan is passed (usually unused)",
    )
    init_cmd.add_argument(
        "--pin-sha",
        action="store_true",
        help=(
            "With --lockless, pin uses: roham-amd/auctelis@<commit-sha> # vX "
            "(resolves the release tag; exit 2 without --lockless)"
        ),
    )
    init_cmd.add_argument(
        "--action-sha",
        metavar="SHA",
        help=(
            "With --lockless, pin the Action to this 40-hex commit offline "
            "(no tag lookup; exit 2 without --lockless)"
        ),
    )

    status_cmd = sub.add_parser(
        "status",
        help="Show lock / workflow / CODEOWNERS / protection status",
    )
    status_cmd.add_argument("path", type=Path, nargs="?", default=Path("."))
    status_cmd.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit nonzero when comment-only is broken, or when enforce (locked=true) is not armed"
        ),
    )
    status_cmd.add_argument(
        "--require-protection",
        action="store_true",
        help=(
            "Hard-fail when the code-owner ruleset cannot be verified (CI / strict); "
            "offline local status says 'verify in GitHub' instead"
        ),
    )

    # Keep the alias runnable, but omit it from public --help.
    ci = sub.add_parser("ci")
    sub._choices_actions = [item for item in sub._choices_actions if item.dest != "ci"]
    ci_sub = ci.add_subparsers(dest="ci_command", required=True)
    ci_init = ci_sub.add_parser(
        "init",
        help="Write .auctelis.yml + enforce workflow + CODEOWNERS + AUTHORITY.lock",
    )
    ci_init.add_argument("path", type=Path, nargs="?", default=Path("."))
    ci_init.add_argument("--force", action="store_true")
    ci_init.add_argument(
        "--lockless",
        action="store_true",
        help=(
            "Write only .github/workflows/auctelis.yml (comment-only PR Watch; "
            "no lock, policy, or CODEOWNERS; --owner not required)"
        ),
    )
    ci_init.add_argument(
        "--owner",
        metavar="TEAM",
        help="CODEOWNERS identity for AUTHORITY.lock (e.g. security; @ optional); required",
    )
    ci_init.add_argument(
        "--enforce",
        action="store_true",
        help="Opt into enforce mode (locked=true + strict ruleset); default is comment-only",
    )
    ci_init.add_argument(
        "--advisory",
        action="store_true",
        help="Comment-only mode (default; locked=false)",
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

    trust = sub.add_parser(
        "trust",
        help="Manage trusted destination hosts (tier-1 reach; never secrets/execute)",
    )
    trust.add_argument(
        "hosts",
        nargs="*",
        help="Host(s) to trust, e.g. mcp.linear.app (subdomains are covered)",
    )
    trust.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Repository root (default: cwd)",
    )
    trust.add_argument("--list", action="store_true", help="List trusted hosts")
    trust.add_argument("--remove", action="store_true", help="Remove the given hosts")
    trust.add_argument(
        "--init",
        action="store_true",
        help="Write a starter trusted-host list (opt-in; never automatic)",
    )

    demo = sub.add_parser(
        "demo",
        help="Optional packaged fixture: lock-only Authority Diff on demo-vulnerable",
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

    rollout = sub.add_parser(
        "rollout",
        help="Open lockless Watch PRs from a Reach Report (dry-run unless --apply)",
    )
    rollout.add_argument(
        "report",
        type=Path,
        help="reach-report.json from check --report (single repo or fleet)",
    )
    rollout.add_argument(
        "--apply",
        action="store_true",
        help="Create branches and open PRs (default is a dry-run with no writes)",
    )
    rollout.add_argument(
        "--status",
        action="store_true",
        help=(
            "Read-only funnel ledger: classify Watch PR / workflow state per "
            "target (GET only; mutually exclusive with --apply)"
        ),
    )
    rollout.add_argument(
        "--max-prs",
        type=int,
        default=10,
        metavar="N",
        help="Cap Watch PRs (default: 10)",
    )
    rollout.add_argument(
        "--repo",
        action="append",
        metavar="SLUG",
        dest="repos",
        help="Limit to owner/repo (repeatable; case-insensitive)",
    )
    rollout.add_argument(
        "--min-tier",
        type=int,
        choices=[1, 2],
        default=2,
        metavar="N",
        help="Minimum reach tier to select (1 or 2; default: 2)",
    )
    rollout.add_argument(
        "--org-reusable",
        metavar="ORG",
        help=(
            "Install the 6-line caller of "
            "ORG/.github/.github/workflows/auctelis-org-reusable.yml@main "
            "(defaults from reach-report.json org_reusable when omitted)"
        ),
    )
    rollout.add_argument(
        "--show-body",
        action="store_true",
        help="Dry-run: print each Watch PR body (--json includes a body field)",
    )
    rollout.add_argument(
        "--pin-sha",
        action="store_true",
        help=(
            "Pin lockless uses: roham-amd/auctelis@<commit-sha> # vX "
            "(resolves the release tag; no-op with --org-reusable; "
            "not valid with --status). On GHES pass --action-sha instead"
        ),
    )
    rollout.add_argument(
        "--action-sha",
        metavar="SHA",
        help=(
            "Pin lockless uses: to this 40-hex commit with no tag lookup "
            "(no-op with --org-reusable; not valid with --status). "
            "Required on GHES; does not fall back to api.github.com"
        ),
    )
    rollout.add_argument(
        "--json",
        action="store_true",
        help="Emit rollout JSON",
    )
    rollout.add_argument(
        "--csv",
        action="store_true",
        help="With --status: emit CSV (columns ⊂ eval/pilot-metrics.csv)",
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
        "--accept-gated",
        action="store_true",
        help=(
            "Allow writing a lock when the tree has HIGH/CRITICAL gated findings. "
            "Use for intentional baseline seals; prefer remediating first."
        ),
    )
    lock_cmd.add_argument(
        "--max-files",
        type=int,
        default=None,
        metavar="N",
        help="Inventory walk file cap (default: 50000 or AUCTELIS_MAX_FILES)",
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
    lock_cmd.add_argument(
        "--strict-digests",
        action="store_true",
        help=(
            "With --check: fail on plain-CI / prose representation digest drift "
            "(default: advisory only; Hook body edits always fail)"
        ),
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
        help=(
            "Committed AUTHORITY.lock to compare against the tree (drift check only). "
            "Head authority is always derived from the working tree."
        ),
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
        "--comment-only",
        action="store_true",
        help=(
            "Lockless / advisory mode: post the Authority Diff without failing "
            "the required check on growth (Action locked=false)"
        ),
    )
    gate_cmd.add_argument(
        "--comment-policy",
        choices=["auto", "always"],
        default="auto",
        help=("auto (default): skip the PR comment when nothing changed; always: post on every PR"),
    )
    gate_cmd.add_argument(
        "--agent",
        action="store_true",
        help="Emit JSON gate report",
    )
    gate_cmd.add_argument(
        "--max-files",
        type=int,
        default=None,
        metavar="N",
        help="Inventory walk file cap (default: 50000 or AUCTELIS_MAX_FILES)",
    )
    gate_cmd.add_argument(
        "--strict-digests",
        action="store_true",
        help=(
            "Fail lock↔tree freshness on plain-CI / prose representation digest drift "
            "(default: quiet; Hook body edits always fail; PR comment still shows body changed)"
        ),
    )

    if include_dev:
        # Lazy: auctelis-devtools is source-only; never import from product main.
        from auctelis_devtools.cli.parser_ext import (  # type: ignore[import-not-found]
            add_dev_commands,
        )

        add_dev_commands(sub)

    diff_parser = sub.add_parser(
        "diff",
        help="Local PR Authority Diff simulator (`--base <ref>` or `lock`)",
    )
    diff_parser.add_argument(
        "--base",
        metavar="REF",
        help=(
            "Git ref for the approved base: tree-truth extract via detached "
            "worktree first (Action parity); committed lock is fallback / drift signal"
        ),
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

    return parser
