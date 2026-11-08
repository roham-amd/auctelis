"""Argparse construction for the authdiff CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_EPILOG = """
public core:  demo → doctor → vet/open → scan/check → lock → ci init
review:       explain | diff lock | delta | annotate | fix/harden  (optional)
advanced:     run | snapshot | artifact-vet | atlas | lsp-validate | manifests
              (omitted from brief help — see docs/CLI-REFERENCE.md)
maintainer:   authdiff-dev only (build | lint | corpus | benchmark | …)

Bare `authdiff` (or a path / scan flags) defaults to `scan .`.
Passive scans never execute target code.
`run` / `snapshot --execute` are env-scrub only (NOT a sandbox).
Target `.authdiff.yml` is ignored unless `--policy` or `--trust-target-policy` is set.
Commit AUTHORITY.lock and protect it with CODEOWNERS for PR authority review.
Agents must set AUTHDIFF_AGENT=1 and must not run lock / ci init / policy edits.
"""

# Hidden from default --help; still fully callable.
_ADV = argparse.SUPPRESS

# Enforceable public mental model — six jobs, not six brand names.
CORE_PUBLIC_COMMANDS = frozenset({"demo", "doctor", "vet", "open", "scan", "check", "lock", "ci"})

_PRODUCT_COMMANDS = frozenset(
    {
        "scan",
        "check",
        "delta",
        "ci",
        "doctor",
        "vet",
        "open",
        "demo",
        "harden",
        "fix",
        "init-manifest",
        "verify-manifest",
        "init-gate",
        "init",
        "lock",
        "explain",
        "baseline",
        "diff",
        "annotate",
        "run",
        "snapshot",
        "artifact-vet",
        "atlas",
        "lsp-validate",
    }
)

_DEV_COMMANDS = frozenset(
    {
        "build",
        "validate",
        "graph",
        "inventory",
        "audit",
        "preflight",
        "verify",
        "export",
        "pilots",
        "hosts",
        "corpus",
        "benchmark",
        "deps",
        "lint",
    }
)


def normalize_argv(
    argv: Sequence[str] | None,
    *,
    include_dev: bool = False,
) -> list[str]:
    """Default bare / path invocations to ``scan``.

    ``authdiff`` → ``scan .``
    ``authdiff /repo`` → ``scan /repo``
    ``authdiff --locked`` → ``scan --locked``
    Known subcommands and ``-h`` / ``--help`` are left unchanged.
    """
    raw = list(sys.argv[1:] if argv is None else argv)
    known = set(_PRODUCT_COMMANDS)
    if include_dev:
        known |= _DEV_COMMANDS
    if not raw:
        return ["scan", "."]
    head = raw[0]
    if head in ("-h", "--help") or head in known:
        return raw
    return ["scan", *raw]


def build_parser(*, include_dev: bool = False) -> argparse.ArgumentParser:
    prog = "authdiff-dev" if include_dev else "authdiff"
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "authdiff — the authority lockfile and PR security gate for AI agents. "
            "Discover, lock, diff, and require review when agent authority expands. "
            "(Maintainer cmds: `authdiff-dev`)"
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    scan = sub.add_parser(
        "scan",
        aliases=["check"],
        help="Repo authority scan (default when no subcommand; add --locked)",
    )
    delta = sub.add_parser(
        "delta",
        help=_ADV,
    )
    delta.add_argument("path", type=Path, nargs="?", default=Path("."))
    delta.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Prior baseline.json for authority / finding delta",
    )
    delta.add_argument("-o", "--output-dir", type=Path)
    delta.add_argument("--fail-on", choices=["never", "high", "any"], default="high")
    delta.add_argument("--policy", type=Path)
    delta.add_argument("--trust-target-policy", action="store_true")
    delta.add_argument("--no-policy", action="store_true")
    delta.add_argument("--agent", action="store_true")
    delta.set_defaults(save_baseline=None)

    ci = sub.add_parser("ci", help="CI helpers (init workflow + advisory policy)")
    ci_sub = ci.add_subparsers(dest="ci_command", required=True)
    ci_init = ci_sub.add_parser("init", help="Write advisory .authdiff.yml + consumer workflow")
    ci_init.add_argument("path", type=Path, nargs="?", default=Path("."))
    ci_init.add_argument("--force", action="store_true")
    ci_init.set_defaults(command="ci")
    scan.add_argument("path", type=Path, nargs="?", default=Path("."))
    scan.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory (default: ./authdiff-out in the current working directory)",
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
        help="Exit non-zero when findings match policy (default: never, or .authdiff.yml)",
    )
    scan.add_argument(
        "--policy",
        type=Path,
        help="Path to .authdiff.yml (default: only inside the scan target tree)",
    )
    scan.add_argument(
        "--no-policy",
        action="store_true",
        help="Ignore .authdiff.yml even if present",
    )
    scan.add_argument(
        "--trust-target-policy",
        action="store_true",
        help=(
            "Load <target>/.authdiff.yml (including suppressions). "
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
        "--agent",
        action="store_true",
        help="Emit compact agent JSON digest instead of the text map",
    )

    vet = sub.add_parser(
        "vet",
        help="Pre-install verdict for a local path or GitHub URL (safe shallow clone)",
        aliases=["open"],
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
        help="First-run aha: scan demo-vulnerable and print the Authority Diff comment",
    )
    demo.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory (default: ./authdiff-out-demo)",
    )
    demo.add_argument(
        "--fail-on",
        choices=["never", "high", "any"],
        default="high",
        help="Exit policy for the demo scan (default: high)",
    )

    harden = sub.add_parser(
        "harden",
        help=_ADV,
        aliases=["fix"],
    )
    harden.add_argument(
        "--findings",
        type=Path,
        default=Path("authdiff-out/findings.json"),
        help="Path to findings.json (default: authdiff-out/findings.json)",
    )
    harden.add_argument(
        "--apply",
        action="store_true",
        help="Request automatic apply (disabled; always dry-run in this release)",
    )

    init_manifest = sub.add_parser(
        "init-manifest",
        help=_ADV,
    )
    init_manifest.add_argument("path", type=Path, nargs="?", default=Path("."))
    init_manifest.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing AUTHORITY.yml",
    )

    verify_manifest = sub.add_parser(
        "verify-manifest",
        help=_ADV,
    )
    verify_manifest.add_argument("path", type=Path, nargs="?", default=Path("."))
    verify_manifest.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional path to write the verify report JSON",
    )

    init_gate = sub.add_parser(
        "init-gate",
        help=_ADV,
        aliases=["init"],
    )
    init_gate.add_argument("path", type=Path, nargs="?", default=Path("."))
    init_gate.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .authdiff.yml / workflow stub",
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
            "Record a human approval binding (owner identity) on the written lock. "
            "Required for accountable expansions; agents must not set this."
        ),
    )

    explain = sub.add_parser("explain", help=_ADV)
    explain.add_argument("finding_id", help="Finding id such as F-001")
    explain.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("authdiff-out"),
        help="Directory containing findings.json (default: authdiff-out)",
    )
    explain.add_argument(
        "--agent",
        action="store_true",
        help="Emit structured remediation JSON for agents",
    )

    baseline = sub.add_parser("baseline", help=_ADV)
    baseline_sub = baseline.add_subparsers(dest="baseline_cmd", required=True)
    b_save = baseline_sub.add_parser("save", help="Save baseline from findings.json")
    b_save.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("authdiff-out"),
        help="Scan output directory containing findings.json",
    )
    b_save.add_argument(
        "--path",
        type=Path,
        help="Baseline destination (default: <output-dir>/baseline.json)",
    )
    b_show = baseline_sub.add_parser("show", help="Print a baseline.json")
    b_show.add_argument("path", type=Path, nargs="?", default=Path("authdiff-out/baseline.json"))

    if include_dev:
        _add_dev_commands(sub)

    diff_parser = sub.add_parser("diff", help=_ADV)
    diff_sub = diff_parser.add_subparsers(dest="diff_kind", required=True)
    diff_rep = diff_sub.add_parser("report", help="Diff two audit report JSON files")
    diff_rep.add_argument("base", type=Path)
    diff_rep.add_argument("target", type=Path)
    diff_gr = diff_sub.add_parser("graph", help="Diff two ecosystem graph JSON files")
    diff_gr.add_argument("base", type=Path)
    diff_gr.add_argument("target", type=Path)
    diff_risk = diff_sub.add_parser(
        "risk",
        help="Diff current findings.json against a baseline.json",
    )
    diff_risk.add_argument("baseline", type=Path)
    diff_risk.add_argument("findings", type=Path)
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
        default=Path("authdiff-out/findings.json"),
        help="Path to findings.json (default: authdiff-out/findings.json)",
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

    run_cmd = sub.add_parser(
        "run",
        help=_ADV,
    )
    run_cmd.add_argument(
        "--lock",
        type=Path,
        help="Optional AUTHORITY.lock / AUTHORITY.lock.json",
    )
    run_cmd.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command after -- , e.g. authdiff run -- npx -y server",
    )

    snap = sub.add_parser(
        "snapshot",
        help=_ADV,
    )
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

    art = sub.add_parser(
        "artifact-vet",
        help=_ADV,
    )
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

    atlas = sub.add_parser("atlas", help=_ADV)
    atlas_sub = atlas.add_subparsers(dest="atlas_cmd", required=True)
    atlas_crawl = atlas_sub.add_parser("crawl", help="Scan seed repos into docs/atlas/ledger")
    atlas_crawl.add_argument(
        "--seed",
        type=Path,
        help="JSON seed file ({repos:[…]} or list)",
    )
    atlas_crawl.add_argument(
        "--demo-seed",
        action="store_true",
        help="Include bundled demo/attack-replay seeds",
    )
    atlas_crawl.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Override ledger run directory",
    )

    lsp = sub.add_parser(
        "lsp-validate",
        help=_ADV,
    )
    lsp.add_argument("path", type=Path)

    # argparse still registers help=SUPPRESS choices; drop them from --help listing.
    sub._choices_actions = [a for a in sub._choices_actions if a.help != _ADV]

    return parser


def _add_dev_commands(sub: Any) -> None:
    """Maintainer / research commands — only on ``authdiff-dev``."""
    build = sub.add_parser("build", help="Run build and consistency checks")
    build.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "schemas", "prompts"],
        help="Build target (default: all)",
    )
    build.add_argument("--write", action="store_true", help="Write generated monolith")

    val = sub.add_parser("validate", help="Validate authdiff JSON artifacts")
    val_sub = val.add_subparsers(dest="validate_cmd", required=True)
    rep = val_sub.add_parser("report", help="Validate audit report summary JSON")
    rep.add_argument("path", type=Path)
    rep.add_argument("--no-semantic", action="store_true")
    graph = val_sub.add_parser("graph", help="Validate ecosystem graph JSON")
    graph.add_argument("path", type=Path)
    graph.add_argument("--no-semantic", action="store_true")
    claim = val_sub.add_parser("claim", help="Validate a structured agent claim JSON object")
    claim.add_argument("path", type=Path)

    graph_cmd = sub.add_parser("graph", help="Graph utilities")
    graph_sub = graph_cmd.add_subparsers(dest="graph_cmd", required=True)
    paths = graph_sub.add_parser("paths", help="List auto-discovered attack paths")
    paths.add_argument("path", type=Path)

    inv = sub.add_parser("inventory", help="Passive read-only inventory of a directory")
    inv.add_argument("path", type=Path)
    inv.add_argument("-o", "--output", type=Path, help="Write JSON to file")

    audit = sub.add_parser("audit", help="Unified passive assessment package")
    audit.add_argument("path", type=Path, nargs="?", default=Path("."))
    audit.add_argument("--profile", choices=["quick", "standard", "deployment"], default="standard")
    audit.add_argument("-o", "--output-dir", type=Path)

    pre = sub.add_parser("preflight", help="Alias of audit --profile quick")
    pre.add_argument("path", type=Path, nargs="?", default=Path("."))
    pre.add_argument("-o", "--output-dir", type=Path)

    verify = sub.add_parser("verify", help="Supply-chain verification helpers")
    verify_sub = verify.add_subparsers(dest="verify_cmd", required=True)
    digest = verify_sub.add_parser("digest", help="Compute or verify SHA-256 of a file")
    digest.add_argument("path", type=Path)
    digest.add_argument("--expected", help="Expected sha256 hex digest")
    manifest = verify_sub.add_parser("manifest", help="Build passive digest manifest")
    manifest.add_argument("path", type=Path)
    manifest.add_argument("-o", "--output", type=Path)

    export = sub.add_parser("export", help="Export interoperable formats")
    export_sub = export.add_subparsers(dest="export_cmd", required=True)
    sarif_cmd = export_sub.add_parser("sarif", help="Export SARIF 2.1.0")
    sarif_cmd.add_argument("report", type=Path)
    sarif_cmd.add_argument("-o", "--output", type=Path)

    pilots = sub.add_parser("pilots", help="Run curated pilot-repository Guard scans")
    pilots_sub = pilots.add_subparsers(dest="pilots_cmd", required=True)
    pilots_run = pilots_sub.add_parser("run", help="Scan enabled pilots")
    pilots_run.add_argument("--manifest", type=Path)
    pilots_run.add_argument("-o", "--output-dir", type=Path)
    pilots_run.add_argument("--only", nargs="+")
    pilots_list = pilots_sub.add_parser("list", help="List pilots")
    pilots_list.add_argument("--manifest", type=Path)

    hosts = sub.add_parser("hosts", help="List or show agent-host profiles")
    hosts_sub = hosts.add_subparsers(dest="hosts_cmd", required=True)
    hosts_sub.add_parser("list")
    hosts_show = hosts_sub.add_parser("show")
    hosts_show.add_argument("host_id")

    corp = sub.add_parser("corpus", help="Security regression corpus harness")
    corp_sub = corp.add_subparsers(dest="corpus_cmd", required=True)
    corp_sub.add_parser("run")

    bench = sub.add_parser("benchmark", help="AgentSecBench harness")
    bench_sub = bench.add_subparsers(dest="benchmark_cmd", required=True)
    bench_sub.add_parser("run")
    bench_sub.add_parser("rules")
    bench_llm = bench_sub.add_parser("llm")
    bench_llm.add_argument("--submissions", type=Path)
    bench_llm.add_argument("--validate-only", action="store_true")
    bench_llm.add_argument("--split", choices=["public", "held_out", "all"], default="all")
    bench_llm.add_argument("--report", action="store_true")
    bench_llm.add_argument(
        "--provenance",
        choices=["external", "pilot", "sample", "template", "any"],
        default="any",
    )
    bench_sub.add_parser("governance")
    bench_contract = bench_sub.add_parser("contract")
    contract_sub = bench_contract.add_subparsers(dest="contract_cmd", required=True)
    contract_sub.add_parser("verify")
    bench_intake = bench_sub.add_parser("intake")
    bench_intake.add_argument("source", type=Path)
    bench_intake.add_argument("--agent-id", required=True)
    bench_intake.add_argument(
        "--provenance", choices=["external", "pilot", "sample", "template"], default="external"
    )
    bench_intake.add_argument("--dry-run", action="store_true")
    bench_sub.add_parser("intakes")
    bench_sub.add_parser("collection-status")
    bench_pkg = bench_sub.add_parser("submitter-package")
    bench_pkg.add_argument("-o", "--output", type=Path, required=True)

    deps = sub.add_parser("deps", help="Check/upgrade dependencies")
    deps_sub = deps.add_subparsers(dest="deps_cmd", required=True)
    deps_sub.add_parser("outdated")
    dep_up = deps_sub.add_parser("upgrade")
    dep_up.add_argument("--dry-run", action="store_true")

    lint = sub.add_parser("lint", help="Run Ruff on tools + tests")
    lint.add_argument("--fix", action="store_true")
    lint.add_argument("--format", action="store_true", dest="format_code")
    lint.add_argument("--check-format", action="store_true")
