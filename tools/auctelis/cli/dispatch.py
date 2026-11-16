"""Command handlers for the live auctelis / auctelis-dev CLI surface."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from auctelis.authority_lock import (
    build_authority_lock,
    check_locked,
    diff_authority_locks,
    run_lock_command,
)
from auctelis.cli.authority_commands import (
    cmd_check,
    cmd_why,
)
from auctelis.cli.guards import refuse_agent_mutation
from auctelis.export.agent_digest import render_agent_digest
from auctelis.export.annotate import render_github_annotations, render_text_annotations
from auctelis.export.pr_comment import render_authority_diff_comment, render_gate_pr_comment
from auctelis.export.sarif import report_to_sarif
from auctelis.gate import load_lock_owners, render_gate_report, run_gate
from auctelis.hosts.profiles import get_host_profile, list_host_profiles
from auctelis.inventory.collector import collect_inventory, inventory_to_json
from auctelis.jsonio import print_json, read_json, write_json, write_text
from auctelis.lock_io import load_authority_lock
from auctelis.policy import apply_policy_defaults, discover_policy_file, load_policy
from auctelis.security.scan import run_scan
from auctelis.supply_chain.digest import sha256_file, verify_file_digest
from auctelis.validate_report import validate_report_file

# Maintainer modules (build/deps/corpus/lint) import packaging and other
# dev-only deps. Keep them lazy so the product wheel starts with jsonschema alone.


def _print_validation(path: Path, *, ok: bool, issues: list) -> int:
    if not ok:
        for issue in issues:
            loc = f" ({issue.path})" if issue.path else ""
            print(f"{issue.code}{loc}: {issue.message}")
        return 1
    print(f"OK: {path}")
    return 0


def _write_or_print(data: object, output: Path | None) -> int:
    if output is not None:
        write_json(output, data)
        print(f"Wrote {output}")
    else:
        print_json(data)
    return 0


def dispatch(args: argparse.Namespace) -> int:
    command = args.command
    if args.command == "ci":
        return _cmd_init_gate(args) if getattr(args, "ci_command", None) == "init" else 2

    match command:
        case "check":
            return cmd_check(args)
        case "why":
            return cmd_why(args)
        case "init":
            return _cmd_init(args)
        case "status":
            return _cmd_status(args)
        case "scan":
            return _cmd_scan(args)
        case "demo":
            return _cmd_demo(args)
        case "lock":
            return _cmd_lock(args)
        case "gate":
            return _cmd_gate(args)
        case "build":
            return _cmd_build(args)
        case "validate":
            return _cmd_validate(args)
        case "inventory":
            return _cmd_inventory(args)
        case "verify":
            return _cmd_verify(args)
        case "diff":
            return _cmd_diff(args)
        case "export":
            return _cmd_export(args)
        case "annotate":
            return _cmd_annotate(args)
        case "hosts":
            return _cmd_hosts(args)
        case "corpus":
            return _cmd_corpus()
        case "deps":
            return _cmd_deps(args)
        case "lint":
            return _cmd_lint(args)
        case "run":
            return _cmd_run(args)
        case "snapshot":
            return _cmd_snapshot(args)
        case "artifact-vet":
            return _cmd_artifact_vet(args)
        case _:
            return 2


def _cmd_scan(args: argparse.Namespace) -> int:
    """Scan a target. Target ``.auctelis.yml`` is ignored unless explicitly trusted.

    Safe defaults for agent / third-party review:
    - ``--policy PATH`` loads that file
    - ``--trust-target-policy`` opts into discovering ``<target>/.auctelis.yml``
    - otherwise suppressions from the scanned repo cannot blind the auditor
    """
    policy = None
    target_policy_ignored = False
    explicit_policy = getattr(args, "policy", None)
    trust_target = bool(getattr(args, "trust_target_policy", False))
    if not getattr(args, "no_policy", False):
        if explicit_policy is not None:
            policy = load_policy(Path(explicit_policy))
        elif trust_target:
            policy_path = discover_policy_file(args.path, stop_at=args.path)
            if policy_path is not None:
                policy = load_policy(policy_path)
        else:
            discovered = discover_policy_file(args.path, stop_at=args.path)
            if discovered is not None:
                target_policy_ignored = True

    fail_on = apply_policy_defaults(
        policy=policy,
        fail_on=args.fail_on,
        fail_on_from_cli=args.fail_on is not None,
    )
    output_dir = args.output_dir
    if output_dir is None and policy is not None and policy.output_dir is not None:
        output_dir = policy.output_dir
    if getattr(args, "agent", False) and output_dir is None:
        # Agent mode must not default into the target tree / agent cwd surprise.
        output_dir = Path("auctelis-out").resolve()
    baseline = args.baseline
    if baseline is None and policy is not None and policy.baseline is not None:
        baseline = policy.baseline
    # Target-supplied baselines can zero the delta; only honor when policy is trusted.
    # CLI --baseline remains allowed (operator-supplied).
    if (
        baseline is not None
        and policy is None
        and not explicit_policy
        and not trust_target
        and not getattr(args, "baseline", None)
    ):
        baseline = None

    scan, payload, code = run_scan(
        args.path,
        output_dir=output_dir,
        baseline=baseline,
        save_baseline_path=args.save_baseline,
        fail_on=fail_on,
        policy=policy,
        target_policy_ignored=target_policy_ignored,
        full_report=bool(getattr(args, "full", False)),
        default_excludes=not bool(getattr(args, "include_fixtures", False)),
    )
    findings_doc = scan.to_findings_doc()
    findings_doc["suppressions"] = payload.get("suppressions") or []
    findings_doc["suppression_count"] = len(payload.get("suppressions") or [])
    findings_doc["target_policy_ignored"] = target_policy_ignored

    base_lock_path = getattr(args, "base_lock", None)
    base_lock_delta: dict[str, Any] | None = None
    if base_lock_path is not None and Path(base_lock_path).is_file():
        try:
            head_lock = build_authority_lock(args.path, scan=scan)
            base_lock_delta = diff_authority_locks(
                load_authority_lock(Path(base_lock_path)),
                head_lock,
            )
            payload["base_lock_delta"] = base_lock_delta
            write_json(Path(payload["output_dir"]) / "base-lock-delta.json", base_lock_delta)
            # Advisory only: growth vs the approved (base) lock is the gate's
            # verdict (`auctelis gate`), so scan/check keep writing the delta
            # without failing the job before CODEOWNERS approval can run.
            if base_lock_delta.get("summary", {}).get("meaningful_authority_change"):
                print(
                    "authority delta vs --base-lock is meaningful; "
                    "verdict belongs to `auctelis gate` (scan stays advisory)."
                )
        except (OSError, ValueError, TypeError) as exc:
            print(f"warning: --base-lock ignored ({exc})")

    if getattr(args, "locked", False):
        lock_report, lock_code = check_locked(
            args.path,
            lock_path=getattr(args, "lock_file", None),
            scan=scan,
        )
        payload["authority_lock"] = lock_report
        if lock_code and code == 0:
            code = lock_code
        lock_delta = (
            base_lock_delta
            if isinstance(base_lock_delta, dict)
            else (lock_report.get("delta") if isinstance(lock_report, dict) else None)
        )
        if (
            isinstance(lock_delta, dict)
            or payload.get("risk_delta_doc")
            or payload.get("risk_delta")
        ):
            # Prefer the full risk-delta document so evidence / new findings
            # survive into the PR comment (summary-only drops them).
            risk_for_comment = payload.get("risk_delta_doc") or (
                {"summary": payload["risk_delta"]} if payload.get("risk_delta") else None
            )
            comment = render_authority_diff_comment(
                findings_doc,
                risk_delta=risk_for_comment,
                authority_delta=payload.get("authority_delta"),
                lock_delta=lock_delta if isinstance(lock_delta, dict) else None,
                policy_mode=payload.get("policy_mode"),
                needs_approval_from=load_lock_owners(args.path),
            )
            payload["pr_comment"] = comment
            write_text(Path(payload["output_dir"]) / "pr-comment.md", comment)
    elif isinstance(base_lock_delta, dict):
        risk_for_comment = payload.get("risk_delta_doc") or (
            {"summary": payload["risk_delta"]} if payload.get("risk_delta") else None
        )
        comment = render_authority_diff_comment(
            findings_doc,
            risk_delta=risk_for_comment,
            authority_delta=payload.get("authority_delta"),
            lock_delta=base_lock_delta,
            policy_mode=payload.get("policy_mode"),
            needs_approval_from=load_lock_owners(args.path),
        )
        payload["pr_comment"] = comment
        write_text(Path(payload["output_dir"]) / "pr-comment.md", comment)

    if getattr(args, "agent", False):
        # Never put raw findings in ``extra`` — ``digest.update`` would overwrite
        # the fenced ``gated`` / ``gated_findings`` lists from render_agent_digest.
        _emit_agent_digest(
            findings_doc,
            risk_delta={"summary": payload["risk_delta"]} if payload.get("risk_delta") else None,
            write_to=Path(payload["output_dir"]) / "agent-digest.json",
            extra={
                "target_policy_ignored": target_policy_ignored,
            },
        )
        return code
    print(payload["summary"])
    if payload.get("risk_delta"):
        print_json({"risk_delta": payload["risk_delta"]})
    if payload.get("baseline_saved"):
        print(f"Baseline saved: {payload['baseline_saved']}")
    if payload.get("policy_path"):
        print(f"Policy: {payload['policy_path']}")
    elif target_policy_ignored:
        print("Target .auctelis.yml ignored (pass --trust-target-policy or --policy to apply)")
    # Always surface suppression counts — including agent-adjacent operators.
    print(f"Suppressions applied: {len(payload.get('suppressions') or [])}")
    if payload.get("authority_lock"):
        lock_rep = payload["authority_lock"]
        print(f"AUTHORITY.lock: {lock_rep.get('verdict')}")
        for line in lock_rep.get("lines") or []:
            print(f"  {line}")
    print(f"Artifacts: {payload['output_dir']}")
    return code


def _cmd_lock(args: argparse.Namespace) -> int:
    # `--check` is read-only; writes/updates require a human (not AUCTELIS_AGENT).
    if not bool(getattr(args, "check", False)):
        refused = refuse_agent_mutation("lock")
        if refused is not None:
            return refused

    root = args.path
    lock_path = getattr(args, "lock_file", None)
    mcp_tools: dict[str, str] | None = None
    snap = getattr(args, "snapshot", None)
    if snap is not None:
        from auctelis.mcp_snapshot import snapshot_from_file

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
        approval=getattr(args, "approval", None),
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
    report, code = run_gate(
        args.path,
        base_lock=args.base_lock,
        head_lock=getattr(args, "head_lock", None),
        codeowners_path=getattr(args, "codeowners", None),
        check_ruleset=not bool(getattr(args, "skip_ruleset_check", False)),
        strict_ruleset=bool(getattr(args, "strict_ruleset", True)),
        trust_head_codeowners=bool(getattr(args, "trust_head_codeowners", False)),
        codeowners_from_base=bool(getattr(args, "codeowners", None)),
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
        # Gate owns the sticky comment. Optional findings.json may enrich
        # coverage; it is never required to post the Authority Diff.
        findings_path = gate_out / "findings.json"
        findings_doc = read_json(findings_path) if findings_path.is_file() else None
        if isinstance(findings_doc, dict):
            coverage = findings_doc.get("coverage")
            if isinstance(coverage, dict) and not report.get("coverage"):
                report["coverage"] = coverage
            write_text(
                gate_out / "pr-comment.md",
                render_authority_diff_comment(
                    findings_doc,
                    lock_delta=report.get("delta")
                    if isinstance(report.get("delta"), dict)
                    else None,
                    needs_approval_from=report.get("required_owners") or None,
                    verdict=report.get("verdict"),
                ),
            )
        else:
            write_text(gate_out / "pr-comment.md", render_gate_pr_comment(report))
    return code


def _emit_agent_digest(
    findings_doc: dict[str, Any],
    *,
    risk_delta: dict[str, Any] | None = None,
    write_to: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> int:
    digest = render_agent_digest(findings_doc, risk_delta=risk_delta)
    if extra:
        # Protect fenced / decision fields from accidental overwrite.
        protected = {
            "gated",
            "gated_findings",
            "decision",
            "lead",
            "safety",
            "format",
        }
        for key, value in extra.items():
            if key in protected:
                continue
            digest[key] = value
    if write_to is not None:
        write_json(write_to, digest)
    print_json(digest)
    return 0


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

    dest = Path(tempfile.mkdtemp(prefix="auctelis-demo-"))
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


def _cmd_init(args: argparse.Namespace) -> int:
    """One-command setup: policy + workflow + CODEOWNERS + lock; exit 0 after writes."""
    refused = refuse_agent_mutation("init")
    if refused is not None:
        return refused
    # Prefer apply semantics (merge CODEOWNERS, pin release, probe ruleset).
    args.apply = True
    args.advisory = bool(getattr(args, "advisory", False))
    args.force = bool(getattr(args, "force", False))
    args.accept_gated = bool(getattr(args, "accept_gated", False))
    args.ci_command = "init"
    return _cmd_init_gate(args)


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
    local_action = root / ".github" / "actions" / "auctelis-gate" / "action.yml"
    policy_path = root / ".auctelis.yml"
    lines: list[str] = [f"auctelis status · {root}", f"Product: {product_version()}"]
    problems: list[str] = []
    workflow_strict = True

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
        lines.append("Lock: missing — run `auctelis init --owner security`")
        problems.append("missing AUTHORITY.lock")

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
        lines.append("Policy: missing (.auctelis.yml)")
        problems.append("missing .auctelis.yml")

    if workflow_path.is_file():
        body = workflow_path.read_text(encoding="utf-8")
        has_gate, locked, pin = _workflow_locked_state(body)
        workflow_strict = "--no-strict-ruleset" not in body
        install = "local-action" if local_action.is_file() else "remote-action"
        lines.append(
            f"Workflow: present · gate={'yes' if has_gate else 'NO'} · "
            f"locked={'true' if locked else 'false'} · strict-ruleset="
            f"{'on' if workflow_strict else 'off'} · Action @{pin} · install={install}"
        )
        if not has_gate:
            problems.append("workflow lacks auctelis-gate action")
        if not locked:
            problems.append("workflow locked!=true")
    else:
        lines.append("Workflow: missing — run `auctelis init --owner security`")
        problems.append("missing auctelis-gate.yml")

    co_text = load_codeowners_text(root)
    existing_co = _find_existing_codeowners(root)
    if co_text and codeowners_covers_lock(co_text):
        protection_ok, missing = codeowners_covers_protection(co_text)
        loc = str(existing_co.relative_to(root)).replace("\\", "/") if existing_co else "?"
        if protection_ok:
            lines.append(f"CODEOWNERS: covers protection paths ({loc})")
        else:
            lines.append(
                f"CODEOWNERS: covers AUTHORITY.lock but missing {', '.join(missing)} ({loc})"
            )
            problems.append("CODEOWNERS incomplete protection coverage")
    elif co_text:
        lines.append("CODEOWNERS: present but does not cover AUTHORITY.lock")
        problems.append("CODEOWNERS missing AUTHORITY.lock")
    else:
        lines.append("CODEOWNERS: missing")
        problems.append("missing CODEOWNERS")

    status, detail = check_code_owner_ruleset()
    lines.append(f"Protection: {status} — {detail}")
    # Mirror gate --strict-ruleset: UNVERIFIED/MISSING is not an armed enforce path.
    if check_mode and workflow_strict:
        status_u = str(status or "").upper()
        if status_u == "MISSING":
            problems.append("code-owner review ruleset missing")
        elif status_u == "UNVERIFIED":
            problems.append("ruleset protection UNVERIFIED")
    if check_mode and problems:
        lines.append("Gate armed: NO — " + "; ".join(problems))
    elif check_mode:
        lines.append("Gate armed: YES")
    print("\n".join(lines))
    if check_mode and problems:
        return 1
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
        normalized = str(path).replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
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


def _workflow_locked_state(body: str) -> tuple[bool, bool, str]:
    """Return ``(has_gate_action, locked, pin)`` from an existing workflow body."""
    has_gate = "auctelis-gate" in body and (
        "roham-amd/auctelis" in body or "./.github/actions/auctelis-gate" in body
    )
    locked = bool(re.search(r"locked:\s*[\"']?true[\"']?", body, flags=re.IGNORECASE))
    pin_m = re.search(
        r"(?:roham-amd/auctelis/\.github/actions/auctelis-gate@|auctelis-gate@)([^\s#]+)",
        body,
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
    body = re.sub(
        r"(roham-amd/auctelis/\.github/actions/auctelis-gate@)[^\s#]+",
        rf"\g<1>{pin}",
        workflow_body,
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
    owner = (getattr(args, "owner", None) or "").strip()
    if not owner or owner in {"@YOUR_TEAM", "YOUR_TEAM"}:
        print(
            "ci init requires --owner @team-or-user (refusing placeholder @YOUR_TEAM).\n"
            "Example: auctelis ci init --owner @security-owners"
        )
        return 2
    if not owner.startswith("@"):
        owner = f"@{owner}"
    advisory = bool(getattr(args, "advisory", False))
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
        workflow_body = workflow_body.replace(
            "# Enforce mode: AUTHORITY.lock drift fails the job; CODEOWNERS must review growth.",
            "# Advisory mode: Authority Diff posts; does not fail on lock drift.",
        )
    codeowners_body = codeowners_body.replace("@YOUR_TEAM", owner)
    # Always pin to the installed auctelis release tag — never consumer HEAD.
    workflow_body = _pin_workflow_to_release(workflow_body)
    accept_gated = bool(getattr(args, "accept_gated", False))
    wrote: list[str] = []
    warnings: list[str] = []
    reported_locked = not advisory
    reported_mode = "advisory" if advisory else "enforce"
    if policy_path.exists() and not args.force:
        print(f"Exists (use --force): {policy_path}")
    else:
        policy_path.write_text(policy_body, encoding="utf-8")
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
            workflow_path.write_text(refreshed, encoding="utf-8")
            wrote.append(f"{workflow_path} (pin refreshed)")
        else:
            print(
                f"Exists (skipped workflow rewrite without --force): {workflow_path} "
                f"[gate={'yes' if has_gate else 'no'}, locked={str(existing_locked).lower()}]"
            )
    else:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(workflow_body, encoding="utf-8")
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
            str(rec.get("path") or "").replace("\\", "/").lstrip("./")
            for rec in (init_lock.get("records") or [])
            if isinstance(rec, dict) and rec.get("path")
        }
    )
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
            codeowners_path.write_text(merged, encoding="utf-8")
            wrote.append(f"{codeowners_path} (merged)")
        else:
            print(f"CODEOWNERS already covers protection paths: {codeowners_path}")
    else:
        codeowners_path.parent.mkdir(parents=True, exist_ok=True)
        seeded = _merge_codeowners_authority(codeowners_body, owner, extra_paths=discovered_paths)
        codeowners_path.write_text(seeded, encoding="utf-8")
        wrote.append(str(codeowners_path))
    lock_path = root / "AUTHORITY.lock"
    # Always (re)seal after generated workflow/policy so CI authority is in the lock.
    msg, lock_code = run_lock_command(
        root,
        lock_path=lock_path,
        check=False,
        update=True,
        approval=None,
        accept_gated=accept_gated,
    )
    print(msg)
    if lock_code != 0:
        warnings.append(
            "AUTHORITY.lock not sealed — remediate configs (unparsed/gated) then re-run. "
            "(CODEOWNERS remains the approval system)."
        )
    else:
        wrote.append(f"{lock_path} (sealed)")
    if wrote:
        print("Wrote:")
        for path in wrote:
            print(f"  {path}")
    pin = _resolve_action_pin_ref()
    print(f"Action pin: roham-amd/auctelis/.github/actions/auctelis-gate@{pin}")
    print("Next: git add AUTHORITY.lock .auctelis.yml .github/ && open a PR")
    print(
        f"CODEOWNERS owner: {owner}. "
        f"Actual workflow: mode={reported_mode} (locked: {str(reported_locked).lower()})."
    )
    if apply:
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


def _cmd_build(args: argparse.Namespace) -> int:
    from auctelis.build import build_all, sync_schemas

    match args.target:
        case "schemas":
            for line in sync_schemas():
                print(line)
        case _:
            print_json(build_all())
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    semantic = not getattr(args, "no_semantic", False)
    if args.validate_cmd != "report":
        return 2
    report_result = validate_report_file(args.path, semantic=semantic)
    return _print_validation(args.path, ok=report_result.ok, issues=report_result.issues)


def _cmd_inventory(args: argparse.Namespace) -> int:
    result = collect_inventory(args.path)
    return _write_or_print(inventory_to_json(result), args.output)


def _cmd_verify(args: argparse.Namespace) -> int:
    if args.verify_cmd != "digest":
        return 2
    if args.expected:
        ok, actual = verify_file_digest(args.path, args.expected)
        print_json({"ok": ok, "sha256": actual})
        return 0 if ok else 1
    print_json({"sha256": sha256_file(args.path)})
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


def _cmd_export(args: argparse.Namespace) -> int:
    if args.export_cmd != "sarif":
        return 2
    sarif_doc = report_to_sarif(read_json(args.report))
    if args.output:
        write_json(args.output, sarif_doc)
        count = len(sarif_doc["runs"][0]["results"])
        print(f"Wrote {args.output} ({count} results)")
    else:
        print_json(sarif_doc)
    return 0


def _cmd_annotate(args: argparse.Namespace) -> int:
    if not args.findings.is_file():
        print(f"Findings not found: {args.findings}")
        return 1
    doc = read_json(args.findings)
    if args.annotate_format == "pr-comment":
        risk = None
        risk_path = getattr(args, "risk_delta", None)
        if risk_path and Path(risk_path).is_file():
            risk = read_json(Path(risk_path))
        text = render_authority_diff_comment(doc, risk_delta=risk)
    elif args.annotate_format == "text":
        text = render_text_annotations(doc)
    else:
        text = render_github_annotations(doc)
    if text:
        print(text, end="" if text.endswith("\n") else "\n")
    else:
        print("No SECURITY_FINDING/EXPOSURE annotations.")
    return 0


def _cmd_hosts(args: argparse.Namespace) -> int:
    match args.hosts_cmd:
        case "list":
            print_json({"hosts": list_host_profiles()})
            return 0
        case "show":
            profile = get_host_profile(args.host_id)
            if profile is None:
                print(f"Unknown host profile: {args.host_id}")
                print("Known:", ", ".join(sorted(p["host_id"] for p in list_host_profiles())))
                return 1
            print_json(profile.to_dict())
            return 0
        case _:
            return 2


def _cmd_corpus() -> int:
    from auctelis.corpus.runner import run_corpus

    summary = run_corpus()
    print_json(summary)
    return 0 if summary.get("failed", 0) == 0 else 1


def _cmd_deps(args: argparse.Namespace) -> int:
    from auctelis.deps import outdated_report, upgrade_pins

    match args.deps_cmd:
        case "outdated":
            report = outdated_report()
            print_json(report)
            return 1 if report.get("outdated_count") or report.get("errors") else 0
        case "upgrade":
            result = upgrade_pins(dry_run=args.dry_run, requires_python=">=3.12")
            print_json(result)
            return 0 if result.get("ok") else 1
        case _:
            return 2


def _cmd_lint(args: argparse.Namespace) -> int:
    from auctelis.lint import run_ruff

    summary = run_ruff(
        fix=args.fix,
        format_code=args.format_code,
        check_format=args.check_format and not args.format_code,
    )
    return 0 if summary.get("ok") else 1


def _cmd_run(args: argparse.Namespace) -> int:
    from auctelis.broker import run_brokered

    cmd = list(args.command or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("usage: auctelis run [--lock AUTHORITY.lock] -- <command…>")
        return 2
    return run_brokered(cmd, lock_path=args.lock)


def _cmd_snapshot(args: argparse.Namespace) -> int:
    from auctelis.jsonio import print_json, write_json
    from auctelis.mcp_snapshot import snapshot_execute, snapshot_from_file

    if args.from_file:
        doc = snapshot_from_file(args.from_file)
    elif args.execute is not None:
        cmd = list(args.execute or [])
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            print("usage: auctelis-dev snapshot --execute -- <command…>")
            return 2
        doc = snapshot_execute(cmd, allow_network=bool(args.allow_network))
    else:
        print("usage: auctelis-dev snapshot --from-file tools.json | --execute -- <cmd>")
        return 2
    if args.output:
        write_json(args.output, doc)
        print(f"Wrote {args.output}")
    else:
        print_json(doc)
    return 0 if doc.get("ok", True) else 1


def _cmd_artifact_vet(args: argparse.Namespace) -> int:
    from auctelis.artifact_vet import run_artifact_vet, write_artifact_report
    from auctelis.jsonio import print_json

    report = run_artifact_vet(args.spec)
    if args.output:
        write_artifact_report(report, args.output)
        print(f"Wrote {args.output}")
    print_json(report.to_dict())
    return 0 if report.verdict == "ALLOW_WITH_GAPS" else 1
