"""Product command handlers and the CLI dispatcher.

Product surface: ``check``, ``lock``, ``init``, ``status``, ``gate``, ``diff``,
``trust``, ``why``, ``demo``, and the ``ci`` alias. Maintainer / research
handlers live in :mod:`auctelis_devtools` (``auctelis-dev`` only).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
from pathlib import Path

from auctelis.authority_lock import (
    build_authority_lock,
    diff_authority_locks,
    run_lock_command,
)
from auctelis.cli.authority_commands import (
    cmd_check,
    cmd_why,
)
from auctelis.cli.guards import refuse_agent_mutation, require_research
from auctelis.export.pr_comment import (
    render_authority_diff_comment,
    render_first_run_comment,
    render_gate_pr_comment,
)
from auctelis.gate import render_gate_report, run_gate
from auctelis.jsonio import print_json, read_json, write_json, write_text
from auctelis.lock_io import load_authority_lock
from auctelis.policy import load_policy
from auctelis.textutil import sanitize_terminal_line

# Materialized packaged-demo trees; TemporaryDirectory finalizers clean them up.
_DEMO_TEMP_DIRS: list[object] = []


def dispatch(args: argparse.Namespace) -> int:
    command = args.command
    if args.command == "ci":
        return _cmd_init_gate(args) if getattr(args, "ci_command", None) == "init" else 2

    match command:
        case "check":
            return cmd_check(args)
        case "why":
            return cmd_why(args)
        case "trust":
            return _cmd_trust(args)
        case "init":
            return _cmd_init(args)
        case "status":
            return _cmd_status(args)
        case "demo":
            return _cmd_demo(args)
        case "lock":
            return _cmd_lock(args)
        case "gate":
            return _cmd_gate(args)
        case "diff":
            return _cmd_diff(args)
        case _:
            return 2


def _apply_max_files_env(args: argparse.Namespace) -> None:
    max_files = getattr(args, "max_files", None)
    if max_files is not None:
        os.environ["AUCTELIS_MAX_FILES"] = str(int(max_files))


def _cmd_lock(args: argparse.Namespace) -> int:
    # `--check` is read-only; writes/updates require a human (not AUCTELIS_AGENT).
    if not bool(getattr(args, "check", False)):
        refused = refuse_agent_mutation("lock")
        if refused is not None:
            return refused
    _apply_max_files_env(args)

    root = args.path
    lock_path = getattr(args, "lock_file", None)
    mcp_tools: dict[str, str] | None = None
    snap = getattr(args, "snapshot", None)
    if snap is not None:
        require_research()
        from auctelis_research.mcp_snapshot import snapshot_from_file

        doc = snapshot_from_file(Path(snap))
        frag = (doc.get("authority_lock_fragment") or {}).get("mcp_tools") or {}
        if not frag and doc.get("tools"):
            frag = {
                str(t.get("name")): str(t.get("description_sha256"))
                for t in doc["tools"]
                if isinstance(t, dict) and t.get("name") and t.get("description_sha256")
            }
        mcp_tools = {str(k): str(v) for k, v in frag.items()}

    text, code = run_lock_command(
        root,
        check=bool(getattr(args, "check", False)),
        update=bool(getattr(args, "update", False)),
        lock_path=lock_path,
        accept_gated=bool(getattr(args, "accept_gated", False)),
        mcp_tools=mcp_tools,
    )
    print(text)
    if code == 0 and bool(getattr(args, "resolve", False)):
        print(
            "Next (opt-in network): auctelis-dev snapshot --execute -- <mcp-launcher…> "
            "then auctelis lock --snapshot tools.json"
        )
    return code


def _cmd_gate(args: argparse.Namespace) -> int:
    """Base→head lock gate: growth label + CODEOWNERS / ruleset check."""
    _apply_max_files_env(args)
    report, code = run_gate(
        args.path,
        base_lock=args.base_lock,
        head_lock=getattr(args, "head_lock", None),
        codeowners_path=getattr(args, "codeowners", None),
        check_ruleset=not bool(getattr(args, "skip_ruleset_check", False)),
        strict_ruleset=bool(getattr(args, "strict_ruleset", True)),
        trust_head_codeowners=bool(getattr(args, "trust_head_codeowners", False)),
        codeowners_from_base=bool(getattr(args, "codeowners", None)),
        comment_only=bool(getattr(args, "comment_only", False)),
    )
    if getattr(args, "agent", False):
        print_json(report)
    else:
        print(render_gate_report(report))
    gate_out_env = os.environ.get("AUCTELIS_OUTPUT_DIR")
    if gate_out_env:
        gate_out = Path(gate_out_env)
        gate_out.mkdir(parents=True, exist_ok=True)
        write_json(gate_out / "gate-report.json", report)
        write_text(gate_out / "gate-report.txt", render_gate_report(report))
        from auctelis.reach_tiers import load_trusted_hosts

        trusted_hosts = load_trusted_hosts(args.path)
        if report.get("trusted_hosts_ignored"):
            # Do not render a lower tier than the verdict actually used.
            trusted_hosts = set()
        comment_path = gate_out / "pr-comment.md"
        skip_path = gate_out / "comment-skip.txt"
        # Quiet on NONE: the Authority Diff comment is the product, but a
        # no-change comment on every PR trains maintainers to disable the Job.
        # Silence is the feature; job summary still records PASS/NONE.
        coverage_raw = report.get("coverage")
        coverage = coverage_raw if isinstance(coverage_raw, dict) else {}
        truncated = bool(coverage.get("truncated"))
        quiet = (
            str(getattr(args, "comment_policy", "auto") or "auto") == "auto"
            and str(report.get("verdict") or "") == "PASS"
            and str(report.get("label") or "NONE") == "NONE"
            and not int(report.get("unparsed") or 0)
            and not bool(report.get("lock_tree_drift"))
            and not bool(report.get("meaningful_authority_change"))
            and not bool(report.get("representation_only"))
            and not truncated
        )
        # Always write the first-run proof payload. Install-shaped PRs often
        # produce GROWTH (new workflow CI record) and would otherwise only write
        # pr-comment.md — leaving the Action unable to post "Watching …".
        write_text(
            gate_out / "comment-first-run.md",
            render_first_run_comment(report),
        )
        if quiet:
            write_text(
                skip_path,
                "No authority change vs base lock — comment skipped "
                "(set comment-on-none: true or --comment-policy always).\n",
            )
            with contextlib.suppress(OSError):
                comment_path.unlink(missing_ok=True)
        else:
            with contextlib.suppress(OSError):
                skip_path.unlink(missing_ok=True)
            # Gate owns the sticky comment. Optional findings.json may enrich
            # coverage; it is never required to post the Authority Diff.
            findings_path = gate_out / "findings.json"
            findings_doc = read_json(findings_path) if findings_path.is_file() else None
            if isinstance(findings_doc, dict):
                cov = findings_doc.get("coverage")
                if isinstance(cov, dict) and not report.get("coverage"):
                    report["coverage"] = cov
                write_text(
                    comment_path,
                    render_authority_diff_comment(
                        findings_doc,
                        lock_delta=report.get("delta")
                        if isinstance(report.get("delta"), dict)
                        else None,
                        needs_approval_from=report.get("required_owners") or None,
                        verdict=report.get("verdict"),
                        mode=str(report.get("mode") or "") or None,
                        trusted_hosts=trusted_hosts,
                    ),
                )
            else:
                write_text(
                    comment_path,
                    render_gate_pr_comment(report, trusted_hosts=trusted_hosts),
                )
    return code


def _init_gate_templates() -> tuple[str, str, str]:
    """Load starter policy + workflow + CODEOWNERS templates."""
    template_dir = Path(__file__).resolve().parents[1] / "templates"
    policy = (template_dir / "auctelis.yml").read_text(encoding="utf-8")
    workflow = (template_dir / "auctelis-gate.yml").read_text(encoding="utf-8")
    codeowners = (template_dir / "CODEOWNERS.snippet").read_text(encoding="utf-8")
    return policy, workflow, codeowners


def _checkout_demo_target() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "examples" / "demo-vulnerable"
        if candidate.is_dir() and (candidate / ".cursor" / "mcp.json").is_file():
            return candidate
    return None


def _packaged_demo_source() -> Path | None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "demo-vulnerable"
    if packaged.is_dir() and (packaged / "skills").is_dir():
        return packaged
    return None


def _materialize_packaged_demo(source: Path) -> Path:
    """Copy packaged fixture into a temp tree with ``.cursor`` / ``.github`` names.

    Setuptools omits dot-directories from wheels, so packaged files use
    ``cursor/`` and ``github/``; adapters still expect the host layout.
    """
    import shutil
    import tempfile

    # Keep the TemporaryDirectory alive for the process lifetime; its finalizer
    # removes the materialized fixture instead of leaking one tree per `demo`.
    tmp = tempfile.TemporaryDirectory(prefix="auctelis-demo-")
    _DEMO_TEMP_DIRS.append(tmp)
    dest = Path(tmp.name)
    mapping = (
        (Path("README.md"), Path("README.md")),
        (Path("skills") / "bootstrap" / "SKILL.md", Path("skills") / "bootstrap" / "SKILL.md"),
        (Path("cursor") / "mcp.json", Path(".cursor") / "mcp.json"),
        (Path("github") / "workflows" / "agent.yml", Path(".github") / "workflows" / "agent.yml"),
        # Legacy editable installs may still ship hidden dirs.
        (Path(".cursor") / "mcp.json", Path(".cursor") / "mcp.json"),
        (Path(".github") / "workflows" / "agent.yml", Path(".github") / "workflows" / "agent.yml"),
    )
    for src_rel, dest_rel in mapping:
        src = source / src_rel
        if not src.is_file():
            continue
        out = dest / dest_rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    return dest


def _demo_target() -> Path | None:
    """Locate a runnable demo tree (checkout preferred; else packaged materialize)."""
    checkout = _checkout_demo_target()
    if checkout is not None:
        return checkout
    packaged = _packaged_demo_source()
    if packaged is None:
        return None
    # Already a host-shaped tree (editable install with hidden dirs).
    if (packaged / ".cursor" / "mcp.json").is_file():
        return packaged
    return _materialize_packaged_demo(packaged)


def _cmd_demo(args: argparse.Namespace) -> int:
    """Lock-only walkthrough: inventory + empty→demo Authority Diff PR comment."""
    from auctelis.security.engine import run_authority_inventory

    target = _demo_target()
    if target is None:
        print(
            "demo fixture not found. Reinstall auctelis, or from a checkout: "
            "auctelis check examples/demo-vulnerable"
        )
        return 2
    out = (args.output_dir or Path("auctelis-out-demo")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    print(f"auctelis demo → {target}")
    print("Lock-only walkthrough: empty baseline → demo AUTHORITY.lock growth.")
    scan = run_authority_inventory(target)
    empty = {
        "version": 1,
        "records": [],
        "policy_hash": None,
        "mcp_tools": {},
    }
    head_lock = build_authority_lock(target, scan=scan)
    lock_delta = diff_authority_locks(empty, head_lock)
    print()
    print("Authority delta (empty → demo):")
    for line in lock_delta.get("lines") or []:
        print(f"  {line}")
    if not lock_delta.get("lines"):
        print("  (no lock records)")
    print()
    findings_doc = {
        "findings": [],
        "coverage": scan.coverage if isinstance(scan.coverage, dict) else {},
        "suppression_count": 0,
    }
    comment = render_authority_diff_comment(
        findings_doc,
        lock_delta=lock_delta,
        needs_approval_from=["@security"],
        verdict="NEEDS_REVIEW",
    )
    write_text(out / "pr-comment.md", comment)
    write_json(out / "authority-lock-delta.json", lock_delta)
    print(comment.strip() or "(no PR comment generated)")
    print()
    print(f"Artifacts: {out}")
    print(f"Records sealed in demo lock: {len(head_lock.get('records') or [])}")
    from auctelis.cli.parser import PUBLIC_PATH

    print("Next: auctelis init --owner security  # then open a PR")
    print(f"Then: auctelis {PUBLIC_PATH}")
    return 0


def _trusted_hosts_path(root: Path) -> Path:
    return root.resolve() / ".auctelis" / "trusted-hosts"


def _normalize_trusted_host(raw: str) -> str:
    text = str(raw or "").strip().lower()
    if not text:
        raise ValueError("empty host")
    if "://" in text:
        from urllib.parse import urlsplit

        text = str(urlsplit(text).hostname or "")
    else:
        text = text.split("/", 1)[0]
    text = text.strip().rstrip(".")
    if not text or any(ch in text for ch in " \t#@"):
        raise ValueError(f"not a host: {raw!r}")
    from auctelis.reach_tiers import valid_trusted_host

    if not valid_trusted_host(text):
        raise ValueError(f"not a specific host (no TLD-only/wildcards): {raw!r}")
    return text


def _cmd_trust(args: argparse.Namespace) -> int:
    """Manage `.auctelis/trusted-hosts` — benign reach stays comment-tier."""
    from auctelis.reach_tiers import STARTER_TRUSTED_HOSTS, load_trusted_hosts

    root = getattr(args, "repo", Path(".")).resolve()
    path = _trusted_hosts_path(root)
    raw_hosts = [str(h) for h in (getattr(args, "hosts", None) or []) if str(h).strip()]
    if getattr(args, "init", False):
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            print(f"Trusted hosts already configured: {path}")
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (
            "# Trusted destination hosts (one per line; subdomains covered).\n"
            "# Trust lowers network-only growth to comment tier. Execute,\n"
            "# secrets, approvals, and unattended reach still fail.\n"
            + "\n".join(STARTER_TRUSTED_HOSTS)
            + "\n"
        )
        path.write_text(body, encoding="utf-8", newline="\n")
        print(f"Wrote starter trusted hosts: {path}")
        print("Edit the file to remove any host you do not trust.")
        return 0

    if getattr(args, "remove", False):
        if not raw_hosts:
            print("Usage: auctelis trust --remove <host> [host…]")
            return 2
        try:
            remove = {_normalize_trusted_host(h) for h in raw_hosts}
        except ValueError as exc:
            print(f"auctelis trust: {exc}")
            return 2
        if not path.is_file():
            print("No trusted hosts configured.")
            return 0
        kept: list[str] = []
        removed = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = line.split("#", 1)[0].strip().lower()
            if entry and entry in remove:
                removed += 1
                continue
            kept.append(line)
        path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8", newline="\n")
        print(f"Removed {removed} host(s) from {path}.")
        return 0

    if raw_hosts:
        try:
            hosts = [_normalize_trusted_host(h) for h in raw_hosts]
        except ValueError as exc:
            print(f"auctelis trust: {exc}")
            return 2
        existing = load_trusted_hosts(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        added = [h for h in hosts if h not in existing]
        if added:
            prior = path.read_text(encoding="utf-8").rstrip() + "\n" if path.is_file() else ""
            if not prior:
                prior = "# Trusted destination hosts (one per line; subdomains covered).\n"
            path.write_text(prior + "\n".join(added) + "\n", encoding="utf-8", newline="\n")
            print(f"Trusted {len(added)} host(s): {', '.join(added)}")
        else:
            print("Already trusted: " + ", ".join(hosts))
        print(f"File: {path}")
        return 0

    # Default / --list
    hosts = sorted(load_trusted_hosts(root))
    if not hosts:
        print(
            "No trusted hosts configured. "
            "Add one with `auctelis trust mcp.linear.app` or `auctelis trust --init`."
        )
        return 0
    print(f"Trusted hosts ({len(hosts)}):")
    for host in hosts:
        print(f"  {host}")
    print(f"File: {path}")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    """One-command setup: policy + workflow + CODEOWNERS + lock; exit 0 after writes."""
    refused = refuse_agent_mutation("init")
    if refused is not None:
        return refused
    if bool(getattr(args, "lockless", False)):
        return _cmd_init_lockless(args)
    # Prefer apply semantics (merge CODEOWNERS, pin release, probe ruleset).
    args.apply = True
    args.advisory = bool(getattr(args, "advisory", False))
    args.force = bool(getattr(args, "force", False))
    args.accept_gated = bool(getattr(args, "accept_gated", False))
    args.ci_command = "init"
    return _cmd_init_gate(args)


def _cmd_init_lockless(args: argparse.Namespace) -> int:
    """Write only the comment-only Authority Diff workflow (no lock ceremony).

    Lockless is the lowest-friction first contact: one YAML file, no owner,
    no ``.auctelis.yml``, no CODEOWNERS, no ``AUTHORITY.lock``. The Action's
    tree-truth diff works from the PR base ref alone and stays quiet on NONE.
    """
    if bool(getattr(args, "enforce", False)):
        print(
            "--lockless writes a comment-only workflow and cannot be combined with "
            "--enforce.\nFor enforce, run `auctelis init --owner @team --enforce`."
        )
        return 2
    root = args.path.resolve()
    workflow_dir = root / ".github" / "workflows"
    workflow_path = workflow_dir / "auctelis.yml"
    template_path = Path(__file__).resolve().parents[1] / "templates" / "auctelis-diff.yml"
    workflow_body = _pin_workflow_to_release(template_path.read_text(encoding="utf-8"))
    if workflow_path.exists() and not bool(getattr(args, "force", False)):
        print(f"Exists (use --force): {workflow_path}")
    else:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(workflow_body, encoding="utf-8", newline="\n")
        print(f"Wrote: {workflow_path}")
    pin = _resolve_action_pin_ref()
    print(f"Action pin: roham-amd/auctelis@{pin}")
    print("Next: git add .github/workflows/auctelis.yml")
    print(
        'Commit and open the install PR: it gets one PASS "Watching" comment; '
        "after that, only PRs that change agent authority get the diff."
    )
    print("Lockless: no AUTHORITY.lock, .auctelis.yml, or CODEOWNERS written.")
    print("Optional enforce later: auctelis init --owner @team --enforce")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Show whether the authority gate is armed in this repo."""
    from auctelis.gate import (
        check_code_owner_ruleset,
        codeowners_covers_lock,
        codeowners_covers_protection,
        load_codeowners_text,
    )
    from auctelis.lock_io import AuthorityLockError, load_authority_lock
    from auctelis.versioning import product_version

    root = args.path.resolve()
    check_mode = bool(getattr(args, "check", False))
    lock_path = root / "AUTHORITY.lock"
    workflow_path = root / ".github" / "workflows" / "auctelis-gate.yml"
    # Lockless template may use auctelis.yml instead of auctelis-gate.yml.
    alt_workflow = root / ".github" / "workflows" / "auctelis.yml"
    local_action = root / ".github" / "actions" / "auctelis-gate" / "action.yml"
    policy_path = root / ".auctelis.yml"
    lines: list[str] = [f"auctelis status · {root}", f"Product: {product_version()}"]
    problems: list[str] = []
    workflow_strict = True
    comment_only = False
    locked = False
    has_gate = False

    def _emit() -> None:
        # Lock/policy errors embed repo-controlled field names; keep stdout line-safe.
        print("\n".join(sanitize_terminal_line(line) for line in lines))

    if lock_path.is_file():
        try:
            lock = load_authority_lock(lock_path)
            n = len(lock.get("records") or [])
            audited = lock.get("audited_commit") or "(none)"
            lines.append(f"Lock: present ({n} records) · audited_commit {audited}")
        except AuthorityLockError as exc:
            lines.append(f"Lock: INVALID — {exc}")
            problems.append("invalid AUTHORITY.lock")
    else:
        lines.append("Lock: missing (OK for lockless comment-only)")

    if policy_path.is_file():
        try:
            policy = load_policy(policy_path)
            lines.append(
                f"Policy: {policy_path.name} · mode={policy.mode} · fail_on={policy.fail_on}"
            )
        except ValueError as exc:
            lines.append(f"Policy: INVALID — {exc}")
            problems.append("invalid .auctelis.yml")
    else:
        lines.append("Policy: missing (.auctelis.yml; OK for lockless)")

    workflow_file = (
        workflow_path
        if workflow_path.is_file()
        else (alt_workflow if alt_workflow.is_file() else None)
    )
    if workflow_file is not None:
        body = workflow_file.read_text(encoding="utf-8")
        has_gate, locked, pin = _workflow_locked_state(body)
        comment_only = not locked
        visible_body = _visible_workflow_text(body)
        # Prefer the Action input; fall back to CLI flag presence for older workflows.
        strict_m = re.search(
            r"strict-ruleset:\s*[\"']?(true|false)[\"']?",
            visible_body,
            flags=re.IGNORECASE,
        )
        if strict_m:
            workflow_strict = strict_m.group(1).lower() == "true"
        else:
            workflow_strict = "--no-strict-ruleset" not in visible_body
        install = "local-action" if local_action.is_file() else "remote-action"
        rel = str(workflow_file.relative_to(root)).replace("\\", "/")
        lines.append(
            f"Workflow: {rel} · gate={'yes' if has_gate else 'NO'} · "
            f"locked={'true' if locked else 'false'} · strict-ruleset="
            f"{'on' if workflow_strict else 'off'} · Action @{pin} · install={install}"
        )
        if comment_only:
            lines.append("Mode: comment-only (enforce not on — OK)")
        else:
            lines.append("Mode: enforce (locked=true)")
        if not has_gate:
            problems.append("workflow lacks auctelis-gate action")
    else:
        lines.append("Workflow: missing — run `auctelis init --lockless` (one file, no lock)")
        problems.append("missing auctelis workflow")

    try:
        co_text = load_codeowners_text(root)
    except OSError as exc:
        co_text = ""
        lines.append(f"CODEOWNERS: unreadable — {exc}")
    existing_co = _find_existing_codeowners(root)
    if co_text and codeowners_covers_lock(co_text):
        protection_ok, missing = codeowners_covers_protection(co_text, root=root)
        loc = str(existing_co.relative_to(root)).replace("\\", "/") if existing_co else "?"
        if protection_ok:
            lines.append(f"CODEOWNERS: covers protection paths ({loc})")
        else:
            lines.append(
                f"CODEOWNERS: covers AUTHORITY.lock but missing {', '.join(missing)} ({loc})"
            )
            if locked:
                problems.append("CODEOWNERS incomplete protection coverage")
    elif co_text:
        lines.append("CODEOWNERS: present but does not cover AUTHORITY.lock")
        if locked:
            problems.append("CODEOWNERS missing AUTHORITY.lock")
    else:
        lines.append("CODEOWNERS: missing" + ("" if comment_only else " (required for enforce)"))
        if locked:
            problems.append("missing CODEOWNERS")

    status, detail = check_code_owner_ruleset()
    lines.append(f"Protection: {status} — {detail}")
    require_protection = bool(getattr(args, "require_protection", False))
    offline_unverified = False
    # Enforce path: a *missing* code-owner ruleset is a real local gap. An
    # UNVERIFIED probe is usually "no API token on this laptop" — say "verify
    # in GitHub" instead of a false local failure, unless CI opts into
    # --require-protection (or the caller has a token but insufficient scope).
    if check_mode and locked and workflow_strict:
        status_u = str(status or "").upper()
        if status_u == "MISSING":
            problems.append("code-owner review ruleset missing")
        elif status_u == "UNVERIFIED":
            if require_protection:
                problems.append("ruleset protection UNVERIFIED")
            else:
                offline_unverified = True
                lines.append(
                    "Protection: verify in GitHub — enable require_code_owner_review "
                    "(local status cannot read rulesets without GITHUB_TOKEN)"
                )
    if locked and not lock_path.is_file():
        problems.append("missing AUTHORITY.lock")

    if check_mode:
        hard = [
            p
            for p in problems
            if p.startswith("invalid ")
            or p
            in {
                "workflow lacks auctelis-gate action",
                "missing auctelis workflow",
            }
        ]
        if comment_only and has_gate:
            # Default install is comment-only; do not fail on missing enforce armor.
            if hard:
                lines.append("Comment-only ready: NO — " + "; ".join(hard))
                _emit()
                return 1
            lines.append("Comment-only ready: YES")
            _emit()
            return 0
        if problems:
            lines.append("Gate armed: NO — " + "; ".join(problems))
            _emit()
            return 1
        if offline_unverified:
            lines.append("Gate armed: YES (locally) — verify code-owner ruleset in GitHub")
        else:
            lines.append("Gate armed: YES")
    _emit()
    return 0


def _codeowners_candidates(root: Path) -> list[Path]:
    """GitHub CODEOWNERS search order (first existing file wins)."""
    return [
        root / ".github" / "CODEOWNERS",
        root / "CODEOWNERS",
        root / "docs" / "CODEOWNERS",
    ]


def _find_existing_codeowners(root: Path) -> Path | None:
    for path in _codeowners_candidates(root):
        if path.is_file():
            return path
    return None


def _has_explicit_codeowners_pattern(text: str, pattern: str) -> bool:
    """True when a non-comment CODEOWNERS line starts with ``pattern`` (not via ``*``)."""
    needle = pattern.replace("\\", "/").rstrip("/")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rule = line.split()[0].replace("\\", "/").lstrip("/")
        rule_stem = rule.rstrip("/")
        if rule_stem in {"*", "**"}:
            continue
        if rule_stem == needle or rule_stem.startswith(needle + "/"):
            return True
        if needle.startswith(rule_stem + "/") and rule.endswith("/"):
            return True
    return False


def _rel_authority_path(path: str) -> str:
    """Normalize a repo-relative authority path without stripping leading dots.

    ``str.lstrip("./")`` treats the argument as a *set* of characters, so
    ``.vscode/mcp.json`` wrongly becomes ``vscode/mcp.json``.
    """
    normalized = str(path or "").replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _merge_codeowners_authority(
    existing: str,
    owner: str,
    *,
    extra_paths: list[str] | None = None,
) -> str:
    """Ensure lock / policy / workflow / action / CODEOWNERS / discovered paths."""
    text = existing if existing.endswith("\n") else existing + "\n"
    required = [
        "AUTHORITY.lock",
        ".auctelis.yml",
        ".auctelis/trusted-hosts",
        ".github/workflows/",
        ".github/actions/",
        ".github/CODEOWNERS",
        # Common authority surfaces (init always covers these globs).
        ".mcp.json",
        ".cursor/mcp.json",
        ".claude/settings.json",
        "**/hooks.json",
        "**/SKILL.md",
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/commands/",
    ]
    for path in extra_paths or []:
        normalized = _rel_authority_path(path)
        if normalized and normalized not in required:
            required.append(normalized)
    missing_lines: list[str] = []
    for pattern in required:
        if pattern == ".github/CODEOWNERS" and (
            _has_explicit_codeowners_pattern(text, "CODEOWNERS")
            or _has_explicit_codeowners_pattern(text, ".github/CODEOWNERS")
        ):
            continue
        if not _has_explicit_codeowners_pattern(text, pattern):
            missing_lines.append(f"{pattern} {owner}")
    if not missing_lines:
        return text
    block = "\n# Added by auctelis init\n" + "\n".join(missing_lines) + "\n"
    return text.rstrip() + block


def _visible_workflow_text(body: str) -> str:
    """Strip YAML comments so documented opt-ins never look like live inputs."""
    visible: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("#"):
            continue
        # Inline comment; generated workflows have no ' #' inside values.
        visible.append(line.split(" #", 1)[0])
    return "\n".join(visible)


def _workflow_locked_state(body: str) -> tuple[bool, bool, str]:
    """Return ``(has_gate_action, locked, pin)`` from an existing workflow body.

    Comments are stripped first: templates document ``locked: "true"`` as an
    opt-in, and a comment must never be mistaken for the live Action input.
    """
    visible = _visible_workflow_text(body)
    has_gate = ("roham-amd/auctelis@" in visible and "auctelis" in visible.lower()) or (
        "auctelis-gate" in visible
        and ("roham-amd/auctelis" in visible or "./.github/actions/auctelis-gate" in visible)
    )
    locked = bool(re.search(r"locked:\s*[\"']?true[\"']?", visible, flags=re.IGNORECASE))
    pin_m = re.search(
        r"(?:roham-amd/auctelis/\.github/actions/auctelis-gate@|"
        r"roham-amd/auctelis@|auctelis-gate@)([^\s#]+)",
        visible,
    )
    pin = pin_m.group(1) if pin_m else "(unpinned)"
    return has_gate, locked, pin


def _resolve_action_pin_ref() -> str:
    """Pin the composite Action to this auctelis release tag — never consumer HEAD.

    Consumer-repo ``git rev-parse HEAD`` produced 422s when the SHA does not
    exist in ``roham-amd/auctelis``. The release tag is always valid there.
    """
    from auctelis.versioning import product_version

    return f"v{product_version()}"


def _pin_workflow_to_release(workflow_body: str) -> str:
    """Rewrite Action uses: and pip install pin to the installed product version."""
    pin = _resolve_action_pin_ref()
    # Prefer root Marketplace Action form; still rewrite legacy subpath pins.
    body = re.sub(
        r"roham-amd/auctelis/\.github/actions/auctelis-gate@[^\s#]+",
        f"roham-amd/auctelis@{pin}",
        workflow_body,
    )
    body = re.sub(
        r"(roham-amd/auctelis@)[^\s#]+",
        rf"\g<1>{pin}",
        body,
    )
    body = re.sub(
        r"(git\+https://github\.com/roham-amd/auctelis\.git@)[^#\s\"]+",
        rf"\g<1>{pin}",
        body,
    )
    body = re.sub(
        r"# Pin to an immutable commit SHA[^\n]*",
        f"# Pinned by auctelis to release {pin} (never consumer-repo HEAD)",
        body,
    )
    body = re.sub(
        r"# Pinned by ci init --apply to [^\n]*",
        f"# Pinned by auctelis to release {pin} (never consumer-repo HEAD)",
        body,
    )
    return body


def _cmd_init_gate(args: argparse.Namespace) -> int:
    refused = refuse_agent_mutation("ci init")
    if refused is not None:
        return refused
    if bool(getattr(args, "lockless", False)):
        return _cmd_init_lockless(args)
    owner = (getattr(args, "owner", None) or "").strip()
    if not owner or owner in {"@YOUR_TEAM", "YOUR_TEAM"}:
        print(
            "init requires --owner @team-or-user unless --lockless "
            "(refusing placeholder @YOUR_TEAM).\n"
            "Example: auctelis init --owner @security-owners\n"
            "         auctelis init --lockless   # one-file comment-only workflow"
        )
        return 2
    if not owner.startswith("@"):
        owner = f"@{owner}"
    # Comment-only is the default; --enforce opts into locked + strict ruleset.
    enforce = bool(getattr(args, "enforce", False))
    advisory = (not enforce) or bool(getattr(args, "advisory", False))
    if enforce and getattr(args, "advisory", False):
        print("Pass either --enforce or --advisory, not both.")
        return 2
    apply = bool(getattr(args, "apply", False))
    root = args.path.resolve()
    root.mkdir(parents=True, exist_ok=True)
    policy_path = root / ".auctelis.yml"
    workflow_dir = root / ".github" / "workflows"
    workflow_path = workflow_dir / "auctelis-gate.yml"
    # Prefer an existing CODEOWNERS (root/docs/.github) — never shadow root with
    # a new .github/CODEOWNERS. --force merges; it never wipes other rules.
    existing_codeowners = _find_existing_codeowners(root)
    codeowners_path = existing_codeowners or (root / ".github" / "CODEOWNERS")
    policy_body, workflow_body, codeowners_body = _init_gate_templates()
    if advisory:
        policy_body = policy_body.replace("mode: enforce", "mode: advisory")
        workflow_body = workflow_body.replace('locked: "true"', 'locked: "false"')
        workflow_body = workflow_body.replace('strict-ruleset: "true"', 'strict-ruleset: "false"')
        workflow_body = workflow_body.replace(
            "# Enforce mode: tree-truth Authority Diff fails on unapproved growth;",
            "# Advisory mode: Authority Diff posts; does not fail on lock drift.",
        )
    else:
        policy_body = policy_body.replace("mode: advisory", "mode: enforce")
        workflow_body = workflow_body.replace('locked: "false"', 'locked: "true"')
        workflow_body = workflow_body.replace('strict-ruleset: "false"', 'strict-ruleset: "true"')
    codeowners_body = codeowners_body.replace("@YOUR_TEAM", owner)
    # Always pin to the installed auctelis release tag — never consumer HEAD.
    workflow_body = _pin_workflow_to_release(workflow_body)
    accept_gated = bool(getattr(args, "accept_gated", False))
    wrote: list[str] = []
    warnings: list[str] = []
    # Transactional init: roll back files we created if the lock seal refuses.
    created_paths: list[Path] = []
    prior_text: dict[Path, str | None] = {}

    def _snapshot(path: Path) -> None:
        if path in prior_text:
            return
        prior_text[path] = path.read_text(encoding="utf-8") if path.is_file() else None

    def _write_new(path: Path, body: str) -> None:
        _snapshot(path)
        created = not path.is_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Generated policy/workflow/CODEOWNERS are LF on every OS; git attributes
        # normalize the same way, and Windows editors handle LF fine.
        path.write_text(body, encoding="utf-8", newline="\n")
        if created:
            created_paths.append(path)

    def _rollback_init() -> None:
        for path in reversed(created_paths):
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)
        for path, previous in prior_text.items():
            if path in created_paths:
                continue
            if previous is None:
                continue
            with contextlib.suppress(OSError):
                path.write_text(previous, encoding="utf-8", newline="\n")

    reported_locked = not advisory
    reported_mode = "advisory" if advisory else "enforce"
    if policy_path.exists() and not args.force:
        print(f"Exists (use --force): {policy_path}")
    else:
        _write_new(policy_path, policy_body)
        wrote.append(str(policy_path))
        # Round-trip guard: generated policy must load.
        load_policy(policy_path)
    if workflow_path.exists() and not args.force and not apply:
        print(f"Exists (use --force): {workflow_path}")
    elif workflow_path.exists() and apply and not args.force:
        # Still refresh the Action pin so consumer HEAD never sticks around.
        existing = workflow_path.read_text(encoding="utf-8")
        has_gate, existing_locked, existing_pin = _workflow_locked_state(existing)
        reported_locked = existing_locked
        reported_mode = "enforce" if existing_locked else "advisory"
        if not has_gate:
            warnings.append(
                f"Existing {workflow_path.name} has no auctelis-gate action "
                f"(pin={existing_pin}). Re-run with --force to rewrite."
            )
        refreshed = _pin_workflow_to_release(existing)
        if refreshed != existing:
            _write_new(workflow_path, refreshed)
            wrote.append(f"{workflow_path} (pin refreshed)")
        else:
            print(
                f"Exists (skipped workflow rewrite without --force): {workflow_path} "
                f"[gate={'yes' if has_gate else 'no'}, locked={str(existing_locked).lower()}]"
            )
    else:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        _write_new(workflow_path, workflow_body)
        wrote.append(str(workflow_path))
        has_gate, reported_locked, _pin = _workflow_locked_state(workflow_body)
        reported_mode = "enforce" if reported_locked else "advisory"
    # Inventory first so CODEOWNERS covers discovered authority paths.
    from auctelis.authority_lock import build_authority_lock
    from auctelis.security.engine import run_authority_inventory

    init_scan = run_authority_inventory(root)
    init_lock = build_authority_lock(root, scan=init_scan)
    discovered_paths = sorted(
        {
            _rel_authority_path(str(rec.get("path") or ""))
            for rec in (init_lock.get("records") or [])
            if isinstance(rec, dict) and rec.get("path")
        }
    )
    discovered_paths = [p for p in discovered_paths if p]
    if discovered_paths:
        print("Authority surfaces found:")
        for path in discovered_paths[:20]:
            print(f"  · {path}")
        if len(discovered_paths) > 20:
            print(f"  · … +{len(discovered_paths) - 20} more")

    if codeowners_path.exists():
        # Always merge — never overwrite existing CODEOWNERS (including --force).
        current = codeowners_path.read_text(encoding="utf-8")
        merged = _merge_codeowners_authority(current, owner, extra_paths=discovered_paths)
        if merged != current:
            _write_new(codeowners_path, merged)
            wrote.append(f"{codeowners_path} (merged)")
        else:
            print(f"CODEOWNERS already covers protection paths: {codeowners_path}")
    else:
        seeded = _merge_codeowners_authority(codeowners_body, owner, extra_paths=discovered_paths)
        _write_new(codeowners_path, seeded)
        wrote.append(str(codeowners_path))
    lock_path = root / "AUTHORITY.lock"
    lock_existed = lock_path.is_file()
    _snapshot(lock_path)
    # Always (re)seal after generated workflow/policy so CI authority is in the lock.
    msg, lock_code = run_lock_command(
        root,
        lock_path=lock_path,
        check=False,
        update=True,
        accept_gated=accept_gated,
        scan=init_scan,
    )
    print(msg)
    if lock_code != 0:
        _rollback_init()
        if not lock_existed and lock_path.is_file():
            with contextlib.suppress(OSError):
                lock_path.unlink()
        elif lock_existed and prior_text.get(lock_path) is not None:
            with contextlib.suppress(OSError):
                lock_path.write_text(prior_text[lock_path] or "", encoding="utf-8", newline="\n")
        warnings.append(
            "AUTHORITY.lock not sealed — init rolled back newly written setup files. "
            "Remediate configs (unparsed/gated) then re-run."
        )
        wrote = []
    else:
        wrote.append(f"{lock_path} (sealed)")
    if wrote:
        print("Wrote:")
        for path in wrote:
            print(f"  {path}")
    pin = _resolve_action_pin_ref()
    print(f"Action pin: roham-amd/auctelis@{pin}")
    print("Next: git add AUTHORITY.lock .auctelis.yml .github/ && open a PR")
    print(
        f"CODEOWNERS owner: {owner}. "
        f"Actual workflow: mode={reported_mode} (locked: {str(reported_locked).lower()})."
    )
    if apply and advisory:
        print(
            "Comment-only mode: no ruleset required. Run `auctelis init --owner "
            f"{owner} --enforce` (or `auctelis status --check`) when you want the "
            "required check to fail on growth."
        )
    elif apply:
        from auctelis.gate import check_code_owner_ruleset

        status, detail = check_code_owner_ruleset()
        print(f"Ruleset probe: {status} — {detail}")
        if status != "OK":
            repo = os.environ.get("GITHUB_REPOSITORY") or "<owner>/<repo>"
            warnings.append(
                "Ruleset/branch protection not verified — enable require_code_owner_review "
                f"(https://github.com/{repo}/settings/rules). Files were still written."
            )
            print(
                "Ruleset/branch protection is not verified. Create a ruleset that:\n"
                "  • targets the default branch\n"
                "  • enforcement = active\n"
                "  • require_code_owner_review = true\n"
                f"Settings: https://github.com/{repo}/settings/rules\n"
                "Warning only — setup files were written; exit 0."
            )
        else:
            print("Ruleset verified — growth gate can enforce CODEOWNER review.")
    else:
        print("Enable branch protection requiring a review from that owner on AUTHORITY.lock.")
        print("Or re-run with --apply to merge CODEOWNERS and verify the ruleset.")
    for warning in warnings:
        print(f"Warning: {warning}")
    # Files on disk are the success criterion; protection gaps are warnings.
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    """File lock diff (``diff lock``) or local PR simulator (``diff --base``)."""
    if getattr(args, "diff_kind", None) == "lock":
        delta = diff_authority_locks(
            load_authority_lock(args.base),
            load_authority_lock(args.head),
        )
        if getattr(args, "agent", False):
            print_json(delta)
        else:
            if not delta["lines"]:
                print("No authority lock changes.")
            else:
                print("\n".join(delta["lines"]))
            if delta["summary"].get("policy_changed"):
                print("~ policy_hash changed")
        return 1 if delta["summary"]["authority_changed"] else 0

    base_ref = getattr(args, "base", None)
    if not base_ref:
        print(
            "Usage:\n"
            "  auctelis diff --base <git-ref> [--repo PATH] [--json]\n"
            "  auctelis diff lock <base.lock> <head.lock>"
        )
        return 2
    from auctelis.diff_base import run_diff_base

    text, payload, code = run_diff_base(
        getattr(args, "repo", Path(".")),
        base_ref=str(base_ref),
    )
    if getattr(args, "diff_json", False):
        print_json(payload)
    else:
        print(text)
    return code
