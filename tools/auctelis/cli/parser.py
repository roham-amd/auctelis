"""Argparse construction for the auctelis CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# Single canonical public path — keep README / PRODUCT / INSTALL / ROADMAP in sync.
PUBLIC_PATH = "doctor → lock → scan/gate → ci init  (demo / vet optional)"

_EPILOG = f"""
public core:  {PUBLIC_PATH}
review:       explain | diff lock | annotate | harden  (optional)
maintainer:   auctelis-dev (build | lint | corpus | deps | run | snapshot | …)

Bare `auctelis` → doctor (no repo config) or scan . (AUTHORITY.lock / .auctelis.yml).
Passive scans never execute target code.
Target `.auctelis.yml` is ignored unless `--policy` or `--trust-target-policy` is set.
Commit AUTHORITY.lock and protect it with CODEOWNERS; auctelis labels growth only.
Agents must set AUCTELIS_AGENT=1 and must not run lock / ci init / policy edits.
"""

# Hidden from default --help; still fully callable.
_ADV = argparse.SUPPRESS

# Enforceable public mental model — six jobs, not six brand names.
CORE_PUBLIC_COMMANDS = frozenset({"demo", "doctor", "vet", "scan", "check", "lock", "gate", "ci"})

_PRODUCT_COMMANDS = frozenset(
    {
        "scan",
        "check",
        "ci",
        "doctor",
        "vet",
        "demo",
        "harden",
        "lock",
        "gate",
        "explain",
        "diff",
        "annotate",
    }
)

_DEV_COMMANDS = frozenset(
    {
        "build",
        "validate",
        "inventory",
        "verify",
        "export",
        "hosts",
        "corpus",
        "deps",
        "lint",
        "run",
        "snapshot",
        "artifact-vet",
    }
)


def _cwd_has_repo_config(cwd: Path | None = None) -> bool:
    root = (cwd or Path.cwd()).resolve()
    if (root / "AUTHORITY.lock").is_file():
        return True
    return (root / ".auctelis.yml").is_file() or (root / ".auctelis.yaml").is_file()


def normalize_argv(
    argv: Sequence[str] | None,
    *,
    include_dev: bool = False,
    cwd: Path | None = None,
) -> list[str]:
    """Default bare invocations: doctor (no repo config) or scan .

    ``auctelis`` → ``doctor`` when no AUTHORITY.lock / .auctelis.yml, else ``scan .``
    ``auctelis /repo`` → ``scan /repo``
    ``auctelis --locked`` → ``scan --locked``
    Known subcommands and ``-h`` / ``--help`` are left unchanged.
    """
    raw = list(sys.argv[1:] if argv is None else argv)
    known = set(_PRODUCT_COMMANDS)
    if include_dev:
        known |= _DEV_COMMANDS
    if not raw:
        if _cwd_has_repo_config(cwd):
            return ["scan", "."]
        return ["doctor"]
    head = raw[0]
    if head in ("-h", "--help", "-V", "--version") or head in known:
        return raw
    return ["scan", *raw]


def build_parser(*, include_dev: bool = False) -> argparse.ArgumentParser:
    from auctelis.versioning import package_version, product_version

    prog = "auctelis-dev" if include_dev else "auctelis"
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Auctelis — the authority lockfile and PR security gate for AI agents. "
            "Discover, lock, diff, and require review when agent authority expands. "
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

    scan = sub.add_parser(
        "scan",
        aliases=["check"],
        help="Repo authority scan (default when repo config exists; add --locked)",
    )

    ci = sub.add_parser("ci", help="CI helpers (init workflow + advisory policy)")
    ci_sub = ci.add_subparsers(dest="ci_command", required=True)
    ci_init = ci_sub.add_parser("init", help="Write advisory .auctelis.yml + consumer workflow")
    ci_init.add_argument("path", type=Path, nargs="?", default=Path("."))
    ci_init.add_argument("--force", action="store_true")
    ci_init.add_argument(
        "--owner",
        metavar="@TEAM",
        help="CODEOWNERS identity for AUTHORITY.lock (e.g. @security-owners); required",
    )
    ci_init.set_defaults(command="ci")
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

    doctor = sub.add_parser(
        "doctor",
        help="Map authority on this machine's Cursor/Claude/VS Code host configs",
    )
    doctor.add_argument(
        "--home",
        type=Path,
        help="Override home directory (default: user home; local-only)",
    )
    doctor.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Optional directory for per-surface scan artifacts",
    )
    doctor.add_argument(
        "--fail-on",
        choices=["never", "high", "any"],
        default=None,
        help="Optional exit policy across host surfaces",
    )
    doctor.add_argument(
        "--since-lock",
        action="store_true",
        help="One-screen authority diff vs ~/.auctelis/AUTHORITY.lock (or --lock-file)",
    )
    doctor.add_argument(
        "--lock-file",
        type=Path,
        help="AUTHORITY.lock path for --since-lock (default: ~/.auctelis/AUTHORITY.lock)",
    )
    doctor.add_argument(
        "--agent",
        action="store_true",
        help="Emit compact agent JSON digest instead of the text map",
    )

    vet = sub.add_parser(
        "vet",
        help="Pre-install verdict for a local path or GitHub URL (safe shallow clone)",
    )
    vet.add_argument("source", help="Local path, Git URL, or owner/repo GitHub shorthand")
    vet.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Optional output directory for scan artifacts",
    )
    vet.add_argument(
        "--keep-clone",
        action="store_true",
        help="Keep the temporary clone directory (remote sources only)",
    )
    vet.add_argument(
        "--agent",
        action="store_true",
        help="Emit compact agent JSON digest (verdict + gated findings)",
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

    harden = sub.add_parser(
        "harden",
        help=_ADV,
    )
    harden.add_argument(
        "--findings",
        type=Path,
        default=Path("auctelis-out/findings.json"),
        help="Path to findings.json (default: auctelis-out/findings.json)",
    )
    harden.add_argument(
        "--apply",
        action="store_true",
        help="Request automatic apply (disabled; always dry-run in this release)",
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
            "Deprecated: ignored for gate enforcement. Prefer CODEOWNERS + rulesets. "
            "Still recorded in approved_findings notes when used with --accept-gated."
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
        "--home",
        action="store_true",
        help=(
            "Lock host authority under ~/.auctelis/AUTHORITY.lock "
            "(scans Cursor/Claude/VS Code configs under $HOME)."
        ),
    )
    lock_cmd.add_argument(
        "--snapshot",
        type=Path,
        help="Merge mcp_tools pins from a tools/list snapshot JSON into the lock",
    )
    lock_cmd.add_argument(
        "--resolve",
        action="store_true",
        help=(
            "Opt-in: after locking, remind to run `auctelis snapshot --execute` "
            "for live tools/list pins (no network from lock itself)."
        ),
    )

    gate_cmd = sub.add_parser(
        "gate",
        help="Label authority growth vs base lock; require CODEOWNERS + ruleset",
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
        action="store_true",
        help=(
            "Fail growth when ruleset status is UNVERIFIED "
            "(default: PASS with prominent unverified warning)"
        ),
    )
    gate_cmd.add_argument(
        "--agent",
        action="store_true",
        help="Emit JSON gate report",
    )

    explain = sub.add_parser("explain", help=_ADV)
    explain.add_argument("finding_id", help="Finding id such as F-001")
    explain.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("auctelis-out"),
        help="Directory containing findings.json (default: auctelis-out)",
    )
    explain.add_argument(
        "--agent",
        action="store_true",
        help="Emit structured remediation JSON for agents",
    )

    if include_dev:
        _add_dev_commands(sub)

    diff_parser = sub.add_parser("diff", help=_ADV)
    diff_sub = diff_parser.add_subparsers(dest="diff_kind", required=True)
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

    annotate = sub.add_parser(
        "annotate",
        help=_ADV,
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

    # argparse still registers help=SUPPRESS choices; drop them from --help listing.
    sub._choices_actions = [a for a in sub._choices_actions if a.help != _ADV]

    return parser


def _add_dev_commands(sub: Any) -> None:
    """Maintainer commands — only on ``auctelis-dev`` (research surface removed)."""
    build = sub.add_parser("build", help="Run build and consistency checks")
    build.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "schemas"],
        help="Build target (default: all)",
    )
    build.add_argument("--write", action="store_true", help="Write generated assets")

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
