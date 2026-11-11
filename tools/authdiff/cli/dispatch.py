"""Command handlers for the live authdiff / authdiff-dev CLI surface."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from authdiff.authority_lock import (
    build_authority_lock,
    check_locked,
    diff_authority_locks,
    run_lock_command,
)
from authdiff.build import build_all, sync_schemas
from authdiff.corpus.runner import run_corpus
from authdiff.deps import outdated_report, upgrade_pins
from authdiff.doctor import run_doctor
from authdiff.export.agent_digest import fence_untrusted, render_agent_digest
from authdiff.export.annotate import render_github_annotations, render_text_annotations
from authdiff.export.pr_comment import render_authority_diff_comment
from authdiff.export.sarif import report_to_sarif
from authdiff.gate import load_lock_owners, render_gate_report, run_gate
from authdiff.harden import run_harden
from authdiff.hosts.profiles import get_host_profile, list_host_profiles
from authdiff.inventory.collector import collect_inventory, inventory_to_json
from authdiff.jsonio import print_json, read_json, write_json, write_text
from authdiff.lint import run_ruff
from authdiff.lock_io import load_authority_lock
from authdiff.policy import apply_policy_defaults, discover_policy_file, load_policy
from authdiff.security.engine import ScanResult
from authdiff.security.report import render_finding_explanation
from authdiff.security.scan import run_scan
from authdiff.supply_chain.digest import sha256_file, verify_file_digest
from authdiff.validate_report import validate_report_file
from authdiff.vet import run_vet


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
    # Normalize product-path aliases (open/fix/init/check) to canonical commands.
    command = {
        "open": "vet",
        "fix": "harden",
        "init": "init-gate",
        "check": "scan",
        "delta": "scan",
    }.get(args.command, args.command)
    if args.command == "ci":
        return _cmd_init_gate(args) if getattr(args, "ci_command", None) == "init" else 2

    match command:
        case "scan":
            return _cmd_scan(args)
        case "doctor":
            return _cmd_doctor(args)
        case "vet":
            return _cmd_vet(args)
        case "demo":
            return _cmd_demo(args)
        case "harden":
            return _cmd_harden(args)
        case "init-gate":
            return _cmd_init_gate(args)
        case "lock":
            return _cmd_lock(args)
        case "gate":
            return _cmd_gate(args)
        case "explain":
            return _cmd_explain(args)
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
    """Scan a target. Target ``.authdiff.yml`` is ignored unless explicitly trusted.

    Safe defaults for agent / third-party review:
    - ``--policy PATH`` loads that file
    - ``--trust-target-policy`` opts into discovering ``<target>/.authdiff.yml``
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
        output_dir = Path("authdiff-out").resolve()
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
            # verdict (`authdiff gate`), so scan/check keep writing the delta
            # without failing the job before CODEOWNERS approval can run.
            if base_lock_delta.get("summary", {}).get("meaningful_authority_change"):
                print(
                    "authority delta vs --base-lock is meaningful; "
                    "verdict belongs to `authdiff gate` (scan stays advisory)."
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
        print("Target .authdiff.yml ignored (pass --trust-target-policy or --policy to apply)")
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
    # `--check` is read-only; writes/updates require a human (not AUTHDIFF_AGENT).
    if not bool(getattr(args, "check", False)):
        refused = _refuse_agent_mutation("lock")
        if refused is not None:
            return refused
    from authdiff.authority_lock import home_lock_path
    from authdiff.doctor import discover_host_surfaces

    root = args.path
    lock_path = getattr(args, "lock_file", None)
    if bool(getattr(args, "home", False)):
        home = Path.home()
        # Prefer the first present host surface directory as the scan root.
        surfaces = discover_host_surfaces(home=home)
        present = [s for s in surfaces if s.exists]
        if present:
            root = Path(present[0].path)
            if root.is_file():
                root = root.parent
        else:
            root = home
        lock_path = lock_path or home_lock_path(home)
        lock_path.parent.mkdir(parents=True, exist_ok=True)

    mcp_tools: dict[str, str] | None = None
    snap = getattr(args, "snapshot", None)
    if snap is not None:
        from authdiff.mcp_snapshot import snapshot_from_file

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
            "Next (opt-in network): authdiff snapshot --execute -- <mcp-launcher…> "
            "then authdiff lock --snapshot tools.json"
        )
    return code


def _cmd_gate(args: argparse.Namespace) -> int:
    """Base→head lock gate with CODEOWNERS / PR-approval enforcement."""
    report, code = run_gate(
        args.path,
        base_lock=args.base_lock,
        head_lock=getattr(args, "head_lock", None),
        approved_by=list(getattr(args, "approved_by", None) or []),
        codeowners_path=getattr(args, "codeowners", None),
    )
    if getattr(args, "agent", False):
        print_json(report)
    else:
        print(render_gate_report(report))
    gate_out_env = os.environ.get("AUTHDIFF_OUTPUT_DIR")
    if gate_out_env:
        gate_out = Path(gate_out_env)
        gate_out.mkdir(parents=True, exist_ok=True)
        write_json(gate_out / "gate-report.json", report)
        write_text(gate_out / "gate-report.txt", render_gate_report(report))
    return code


def _cmd_doctor(args: argparse.Namespace) -> int:
    text, code = run_doctor(
        home=getattr(args, "home", None),
        output_dir=getattr(args, "output_dir", None),
        fail_on=getattr(args, "fail_on", None),
    )
    if getattr(args, "agent", False):
        out = getattr(args, "output_dir", None)
        findings_path = None
        if out is not None and Path(out).is_dir():
            candidates = sorted(Path(out).glob("*/findings.json"))
            if candidates:
                findings_path = candidates[0]
        doc: dict[str, Any] = (
            read_json(findings_path)
            if findings_path and findings_path.is_file()
            else {"findings": []}
        )
        _emit_agent_digest(doc)
        return code
    print(text)
    return code


def _cmd_vet(args: argparse.Namespace) -> int:
    text, code = run_vet(
        args.source,
        output_dir=getattr(args, "output_dir", None),
        keep_clone=bool(getattr(args, "keep_clone", False)),
    )
    if getattr(args, "agent", False):
        out = getattr(args, "output_dir", None)
        findings_path = Path(out) / "findings.json" if out else None
        doc = (
            read_json(findings_path)
            if findings_path and findings_path.is_file()
            else {"findings": []}
        )
        _emit_agent_digest(doc)
        return code
    print(text)
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


def _cmd_harden(args: argparse.Namespace) -> int:
    if bool(getattr(args, "apply", False)):
        refused = _refuse_agent_mutation("harden --apply")
        if refused is not None:
            return refused
    text, code = run_harden(
        findings_path=args.findings,
        apply=bool(getattr(args, "apply", False)),
    )
    print(text)
    return code


def _init_gate_templates() -> tuple[str, str, str]:
    """Load starter policy + workflow + CODEOWNERS templates."""
    template_dir = Path(__file__).resolve().parents[1] / "templates"
    policy = (template_dir / "authdiff.yml").read_text(encoding="utf-8")
    workflow = (template_dir / "authdiff-gate.yml").read_text(encoding="utf-8")
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

    dest = Path(tempfile.mkdtemp(prefix="authdiff-demo-"))
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


def _refuse_agent_mutation(command: str) -> int | None:
    """Agents explain evidence; they must not mutate lock/policy/CODEOWNERS."""
    import os

    if os.environ.get("AUTHDIFF_AGENT", "").strip() in {"1", "true", "yes"}:
        print(
            f"refused: `{command}` mutates authority state. "
            "Unset AUTHDIFF_AGENT and have a human run lock / ci init / policy edits."
        )
        return 2
    return None


def _cmd_demo(args: argparse.Namespace) -> int:
    """Run the canned vulnerable fixture and print the Authority Diff (+/- lock lines)."""
    target = _demo_target()
    if target is None:
        print(
            "demo fixture not found. Reinstall authdiff, or from a checkout: "
            "authdiff scan examples/demo-vulnerable --fail-on high"
        )
        return 2
    out = (args.output_dir or Path("authdiff-out-demo")).resolve()
    print(f"authdiff demo → {target}")
    print("Expected: gated findings (unpinned launcher, secrets, HTTP MCP, curl|sh, …)")
    # Demo is an aha walkthrough, not a CI gate — always scan advisory then show +/-.
    scan, payload, _code = run_scan(
        target,
        output_dir=out,
        fail_on="never",
        full_report=False,
    )
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
    comment = render_authority_diff_comment(
        scan.to_findings_doc(),
        risk_delta=payload.get("risk_delta_doc"),
        authority_delta=payload.get("authority_delta"),
        lock_delta=lock_delta,
        policy_mode="advisory",
    )
    write_text(out / "pr-comment.md", comment)
    print(comment.strip() or "(no PR comment generated)")
    print()
    print(f"Artifacts: {out}")
    print(f"Findings: {len(scan.findings)}")
    print("Next: authdiff doctor → open → scan → lock → ci init")
    # First-run aha always exits 0 so install scripts and tutorials succeed.
    return 0


def _cmd_init_gate(args: argparse.Namespace) -> int:
    refused = _refuse_agent_mutation("ci init")
    if refused is not None:
        return refused
    owner = (getattr(args, "owner", None) or "").strip()
    if not owner or owner in {"@YOUR_TEAM", "YOUR_TEAM"}:
        print(
            "ci init requires --owner @team-or-user (refusing placeholder @YOUR_TEAM).\n"
            "Example: authdiff ci init --owner @security-owners"
        )
        return 2
    if not owner.startswith("@"):
        owner = f"@{owner}"
    root = args.path.resolve()
    root.mkdir(parents=True, exist_ok=True)
    policy_path = root / ".authdiff.yml"
    workflow_dir = root / ".github" / "workflows"
    workflow_path = workflow_dir / "authdiff-gate.yml"
    codeowners_path = root / ".github" / "CODEOWNERS"
    policy_body, workflow_body, codeowners_body = _init_gate_templates()
    codeowners_body = codeowners_body.replace("@YOUR_TEAM", owner)
    wrote: list[str] = []
    if policy_path.exists() and not args.force:
        print(f"Exists (use --force): {policy_path}")
    else:
        policy_path.write_text(policy_body, encoding="utf-8")
        wrote.append(str(policy_path))
        # Round-trip guard: generated policy must load.
        load_policy(policy_path)
    if workflow_path.exists() and not args.force:
        print(f"Exists (use --force): {workflow_path}")
    else:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(workflow_body, encoding="utf-8")
        wrote.append(str(workflow_path))
    if codeowners_path.exists() and not args.force:
        print(f"Exists (use --force): {codeowners_path}")
    else:
        codeowners_path.parent.mkdir(parents=True, exist_ok=True)
        codeowners_path.write_text(codeowners_body, encoding="utf-8")
        wrote.append(str(codeowners_path))
    lock_path = root / "AUTHORITY.lock"
    if lock_path.exists() and not args.force:
        print(f"Exists (use --force): {lock_path}")
    else:
        # Initial seal accepts current gated state; CODEOWNERS owner is the approver.
        msg, lock_code = run_lock_command(
            root,
            lock_path=lock_path,
            check=False,
            approval=owner,
            accept_gated=True,
        )
        print(msg)
        if lock_code != 0:
            return lock_code
        wrote.append(str(lock_path))
    if wrote:
        print("Wrote:")
        for path in wrote:
            print(f"  {path}")
    print("Next: git add AUTHORITY.lock .authdiff.yml .github/ && open a PR")
    print(f"CODEOWNERS owner: {owner} (workflow already uses locked: true).")
    print("Enable branch protection requiring a review from that owner on AUTHORITY.lock.")
    print("Pin the Action + tools install to an immutable git tag/SHA (PyPI is not published yet).")
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    findings_path = args.output_dir / "findings.json"
    if not findings_path.is_file():
        print(f"Missing findings.json at {findings_path}. Run `authdiff scan` first.")
        return 1
    doc = read_json(findings_path)
    scan = ScanResult.from_findings_doc(doc)
    finding = scan.finding_by_id(args.finding_id)
    if finding is None:
        print(f"Finding {args.finding_id} not found in {findings_path}")
        return 1
    if getattr(args, "agent", False):
        print_json(
            {
                "finding_id": finding.finding_id,
                "rule_id": finding.rule_id,
                "decision_hint": finding.severity,
                "title": fence_untrusted(finding.title),
                "who_gains": fence_untrusted(finding.attacker_control or finding.entry_point),
                "reach": fence_untrusted(finding.impact),
                "recommended_action": fence_untrusted(finding.recommended_action),
                "fix_snippet": fence_untrusted(finding.fix_snippet),
                "what_would_change_verdict": fence_untrusted(finding.verify_in_60s),
                "evidence_strength": finding.evidence_strength,
                "safety": {"target_is_untrusted_data": True, "evidence_fenced": True},
            }
        )
        return 0
    print(render_finding_explanation(scan, finding))
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
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
    if args.diff_kind != "lock":
        return 2
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
    summary = run_corpus()
    print_json(summary)
    return 0 if summary.get("failed", 0) == 0 else 1


def _cmd_deps(args: argparse.Namespace) -> int:
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
    summary = run_ruff(
        fix=args.fix,
        format_code=args.format_code,
        check_format=args.check_format and not args.format_code,
    )
    return 0 if summary.get("ok") else 1


def _cmd_run(args: argparse.Namespace) -> int:
    from authdiff.broker import run_brokered

    cmd = list(args.command or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("usage: authdiff run [--lock AUTHORITY.lock] -- <command…>")
        return 2
    return run_brokered(cmd, lock_path=args.lock)


def _cmd_snapshot(args: argparse.Namespace) -> int:
    from authdiff.jsonio import print_json, write_json
    from authdiff.mcp_snapshot import snapshot_execute, snapshot_from_file

    if args.from_file:
        doc = snapshot_from_file(args.from_file)
    elif args.execute is not None:
        cmd = list(args.execute or [])
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            print("usage: authdiff snapshot --execute -- <command…>")
            return 2
        doc = snapshot_execute(cmd, allow_network=bool(args.allow_network))
    else:
        print("usage: authdiff snapshot --from-file tools.json | --execute -- <cmd>")
        return 2
    if args.output:
        write_json(args.output, doc)
        print(f"Wrote {args.output}")
    else:
        print_json(doc)
    return 0 if doc.get("ok", True) else 1


def _cmd_artifact_vet(args: argparse.Namespace) -> int:
    from authdiff.artifact_vet import run_artifact_vet, write_artifact_report
    from authdiff.jsonio import print_json

    report = run_artifact_vet(args.spec)
    if args.output:
        write_artifact_report(report, args.output)
        print(f"Wrote {args.output}")
    print_json(report.to_dict())
    return 0 if report.verdict == "ALLOW_WITH_GAPS" else 1
