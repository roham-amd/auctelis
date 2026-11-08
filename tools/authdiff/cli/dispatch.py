"""Command handlers — one cohesive module, low coupling to argparse construction."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

from authdiff.audit import ProfileName, run_audit
from authdiff.audit_diff import diff_graphs, diff_reports
from authdiff.authority_lock import check_locked, diff_authority_locks, run_lock_command
from authdiff.authority_manifest import init_manifest, verify_manifest, write_verify_report
from authdiff.benchmark.governance import verify_dataset_integrity
from authdiff.benchmark.intake import (
    build_submitter_package,
    collection_status,
    intake_submission_dir,
    list_external_intakes,
    verify_evaluation_contract,
)
from authdiff.benchmark.llm_runner import _load_dataset_manifest, run_llm_benchmark
from authdiff.benchmark.report import build_evaluation_report
from authdiff.benchmark.runner import run_benchmark
from authdiff.build import build_all, sync_schemas
from authdiff.corpus.runner import run_corpus
from authdiff.deps import outdated_report, upgrade_pins
from authdiff.doctor import run_doctor
from authdiff.export.agent_digest import fence_untrusted, render_agent_digest
from authdiff.export.annotate import render_github_annotations, render_text_annotations
from authdiff.export.pr_comment import render_authority_diff_comment
from authdiff.export.sarif import report_to_sarif
from authdiff.harden import run_harden
from authdiff.hosts.profiles import get_host_profile, list_host_profiles
from authdiff.inventory.collector import collect_inventory, inventory_to_json
from authdiff.jsonio import print_json, read_json, write_json, write_text
from authdiff.lint import run_ruff
from authdiff.lock_io import load_authority_lock
from authdiff.pilots.runner import load_manifest, run_pilots
from authdiff.policy import apply_policy_defaults, discover_policy_file, load_policy
from authdiff.prompt_build import write_monolith
from authdiff.rules_quality.runner import run_rule_quality
from authdiff.security.baseline import (
    baseline_path,
    diff_against_baseline,
    load_baseline,
    save_baseline,
)
from authdiff.security.engine import ScanResult, run_security_scan
from authdiff.security.report import render_finding_explanation
from authdiff.security.scan import run_scan
from authdiff.supply_chain.digest import sha256_file, verify_file_digest
from authdiff.supply_chain.manifest import build_digest_manifest
from authdiff.validate_report import (
    analyze_graph_paths,
    validate_graph_file,
    validate_report_file,
)
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
        case "init-manifest":
            return _cmd_init_manifest(args)
        case "verify-manifest":
            return _cmd_verify_manifest(args)
        case "init-gate":
            return _cmd_init_gate(args)
        case "lock":
            return _cmd_lock(args)
        case "explain":
            return _cmd_explain(args)
        case "baseline":
            return _cmd_baseline(args)
        case "build":
            return _cmd_build(args)
        case "validate":
            return _cmd_validate(args)
        case "graph":
            return _cmd_graph(args)
        case "inventory":
            return _cmd_inventory(args)
        case "audit":
            return _cmd_audit(args.path, args.profile, args.output_dir)
        case "preflight":
            return _cmd_audit(args.path, "quick", args.output_dir)
        case "verify":
            return _cmd_verify(args)
        case "diff":
            return _cmd_diff(args)
        case "export":
            return _cmd_export(args)
        case "annotate":
            return _cmd_annotate(args)
        case "pilots":
            return _cmd_pilots(args)
        case "hosts":
            return _cmd_hosts(args)
        case "corpus":
            return _cmd_corpus()
        case "benchmark":
            return _cmd_benchmark(args)
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
        case "atlas":
            return _cmd_atlas(args)
        case "lsp-validate":
            return _cmd_lsp_validate(args)
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

    if getattr(args, "locked", False):
        lock_report, lock_code = check_locked(
            args.path,
            lock_path=getattr(args, "lock_file", None),
            scan=scan,
        )
        payload["authority_lock"] = lock_report
        if lock_code and code == 0:
            code = lock_code
        lock_delta = lock_report.get("delta") if isinstance(lock_report, dict) else None
        if isinstance(lock_delta, dict):
            # Refresh PR comment so lock expansions appear in the five-question format.
            comment = render_authority_diff_comment(
                findings_doc,
                risk_delta={"summary": payload["risk_delta"]}
                if payload.get("risk_delta")
                else None,
                authority_delta=payload.get("authority_delta"),
                lock_delta=lock_delta,
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
    text, code = run_lock_command(
        args.path,
        check=bool(getattr(args, "check", False)),
        update=bool(getattr(args, "update", False)),
        lock_path=getattr(args, "lock_file", None),
        approval=getattr(args, "approval", None),
    )
    print(text)
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


def _cmd_init_manifest(args: argparse.Namespace) -> int:
    text, code = init_manifest(args.path, force=bool(args.force))
    print(text)
    return code


def _cmd_verify_manifest(args: argparse.Namespace) -> int:
    report, code = verify_manifest(args.path)
    if getattr(args, "output", None):
        write_verify_report(report, args.output)
        print(f"Wrote {args.output}")
    print_json(report)
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
    """Run the canned vulnerable fixture and print the PR Authority Diff comment."""
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
    scan, payload, code = run_scan(
        target,
        output_dir=out,
        fail_on=args.fail_on,
        full_report=False,
    )
    comment = payload.get("pr_comment") or ""
    print()
    print(comment.strip() or "(no PR comment generated)")
    print()
    print(f"Artifacts: {out}")
    print(f"Findings: {len(scan.findings)} · exit={code}")
    print("Next: authdiff doctor → open → scan → lock → ci init")
    return code


def _cmd_init_gate(args: argparse.Namespace) -> int:
    refused = _refuse_agent_mutation("ci init")
    if refused is not None:
        return refused
    root = args.path.resolve()
    root.mkdir(parents=True, exist_ok=True)
    policy_path = root / ".authdiff.yml"
    workflow_dir = root / ".github" / "workflows"
    workflow_path = workflow_dir / "authdiff-gate.yml"
    codeowners_path = root / ".github" / "CODEOWNERS"
    policy_body, workflow_body, codeowners_body = _init_gate_templates()
    wrote: list[str] = []
    if policy_path.exists() and not args.force:
        print(f"Exists (use --force): {policy_path}")
    else:
        policy_path.write_text(policy_body, encoding="utf-8")
        wrote.append(str(policy_path))
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
        msg, _code = run_lock_command(root, lock_path=lock_path, check=False)
        print(msg)
        wrote.append(str(lock_path))
    if wrote:
        print("Wrote:")
        for path in wrote:
            print(f"  {path}")
    print("Next: git add AUTHORITY.lock .authdiff.yml .github/ && open a PR")
    print("Replace @YOUR_TEAM in .github/CODEOWNERS (workflow already uses locked: true).")
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


def _cmd_baseline(args: argparse.Namespace) -> int:
    match args.baseline_cmd:
        case "save":
            findings_path = args.output_dir / "findings.json"
            if not findings_path.is_file():
                print(f"Missing {findings_path}; run `authdiff scan` first.")
                return 1
            doc = read_json(findings_path)
            # Prefer re-scan of the recorded repository so fingerprints stay current.
            repo = Path(str(doc.get("repository") or ""))
            scan = run_security_scan(repo) if repo.is_dir() else ScanResult.from_findings_doc(doc)
            dest = args.path or baseline_path(args.output_dir)
            saved = save_baseline(scan, dest)
            print(
                f"Wrote baseline with {len(saved.get('finding_keys') or [])} finding keys: {dest}"
            )
            return 0
        case "show":
            if not args.path.is_file():
                print(f"Baseline not found: {args.path}")
                return 1
            print_json(load_baseline(args.path))
            return 0
        case _:
            return 2


def _cmd_build(args: argparse.Namespace) -> int:
    match args.target:
        case "schemas":
            for line in sync_schemas():
                print(line)
        case "prompts":
            # Archived methodology only — not on the product build path.
            print(
                "NOTE: monolith generation is archive/methodology-only "
                "(removed from authdiff-dev build all)."
            )
            print_json(write_monolith(check_only=not args.write))
        case _:
            print_json(build_all())
    return 0


def _validate_claim(path: Path) -> tuple[bool, list[Any]]:
    from dataclasses import dataclass

    @dataclass
    class Issue:
        code: str
        message: str
        path: str = ""

    doc = read_json(path)
    issues: list[Issue] = []
    required = ("claim", "status", "evidence_ids")
    for key in required:
        if key not in doc:
            issues.append(Issue("CLAIM_MISSING_FIELD", f"Missing required field `{key}`"))
    status = doc.get("status")
    allowed = {
        "OBSERVED",
        "CONFIRMED",
        "POTENTIAL",
        "NOT VERIFIED",
        "NOT ASSESSED",
        "NOT APPLICABLE",
    }
    if status is not None and status not in allowed:
        issues.append(Issue("CLAIM_BAD_STATUS", f"Invalid status {status!r}"))
    evidence_ids = doc.get("evidence_ids")
    if evidence_ids is not None and not isinstance(evidence_ids, list):
        issues.append(Issue("CLAIM_BAD_EVIDENCE", "evidence_ids must be a list"))
    if status == "CONFIRMED" and (not evidence_ids):
        issues.append(
            Issue(
                "CLAIM_UNSUPPORTED_CONFIRMED",
                "CONFIRMED claims require non-empty evidence_ids",
            )
        )
    return (len(issues) == 0, issues)


def _cmd_validate(args: argparse.Namespace) -> int:
    semantic = not getattr(args, "no_semantic", False)
    match args.validate_cmd:
        case "report":
            report_result = validate_report_file(args.path, semantic=semantic)
            return _print_validation(args.path, ok=report_result.ok, issues=report_result.issues)
        case "graph":
            graph_result = validate_graph_file(args.path, semantic=semantic)
            return _print_validation(args.path, ok=graph_result.ok, issues=graph_result.issues)
        case "claim":
            ok, issues = _validate_claim(args.path)
            return _print_validation(args.path, ok=ok, issues=issues)
        case _:
            return 2


def _cmd_graph(args: argparse.Namespace) -> int:
    if args.graph_cmd != "paths":
        return 2
    found = analyze_graph_paths(args.path)
    print_json([path.__dict__ for path in found])
    return 0


def _cmd_inventory(args: argparse.Namespace) -> int:
    result = collect_inventory(args.path)
    return _write_or_print(inventory_to_json(result), args.output)


def _cmd_audit(path: Path, profile: str, output_dir: Path | None) -> int:
    payload = run_audit(
        path,
        profile=cast(ProfileName, profile),
        output_dir=output_dir,
    )
    print(payload["summary"])
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    match args.verify_cmd:
        case "digest":
            if args.expected:
                ok, actual = verify_file_digest(args.path, args.expected)
                print_json({"ok": ok, "sha256": actual})
                return 0 if ok else 1
            print_json({"sha256": sha256_file(args.path)})
            return 0
        case "manifest":
            return _write_or_print(build_digest_manifest(args.path), args.output)
        case _:
            return 2


def _cmd_diff(args: argparse.Namespace) -> int:
    match args.diff_kind:
        case "report":
            print_json(diff_reports(read_json(args.base), read_json(args.target)))
            return 0
        case "graph":
            print_json(diff_graphs(read_json(args.base), read_json(args.target)))
            return 0
        case "risk":
            findings = read_json(args.findings)
            repo = findings.get("repository")
            if repo and Path(repo).is_dir():
                scan = run_security_scan(Path(repo))
            else:
                scan = ScanResult.from_findings_doc(findings)
            print_json(diff_against_baseline(scan, load_baseline(args.baseline)))
            return 0
        case "lock":
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
        case _:
            return 2


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


def _cmd_pilots(args: argparse.Namespace) -> int:
    match args.pilots_cmd:
        case "list":
            manifest = load_manifest(args.manifest)
            print_json(
                {
                    "pilots": [
                        {
                            "id": p.get("id"),
                            "path": p.get("path"),
                            "kind": p.get("kind"),
                            "enabled": p.get("enabled", True),
                            "notes": p.get("notes"),
                        }
                        for p in manifest.get("pilots") or []
                    ]
                }
            )
            return 0
        case "run":
            report = run_pilots(
                manifest_path=args.manifest,
                output_dir=args.output_dir,
                only=args.only,
            )
            print_json(
                {
                    "ok_count": report["ok_count"],
                    "pilot_count": report["pilot_count"],
                    "summary": report.get("summary_md"),
                    "results": [
                        {
                            "id": r.get("id"),
                            "status": r.get("status"),
                            "finding_count": r.get("finding_count"),
                            "component_count": r.get("component_count"),
                        }
                        for r in report["results"]
                    ],
                }
            )
            hard_fail = {"missing", "error"}
            return 1 if any(r.get("status") in hard_fail for r in report["results"]) else 0
        case _:
            return 2


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


def _cmd_benchmark(args: argparse.Namespace) -> int:
    match args.benchmark_cmd:
        case "run":
            summary = run_benchmark()
        case "rules":
            summary = run_rule_quality()
        case "governance":
            summary = verify_dataset_integrity(_load_dataset_manifest())
            print_json(summary)
            return 0 if summary.get("ok") else 1
        case "contract":
            if getattr(args, "contract_cmd", None) != "verify":
                return 2
            summary = verify_evaluation_contract()
            print_json(summary)
            return 0 if summary.get("ok") else 1
        case "intake":
            summary = intake_submission_dir(
                args.source,
                agent_id=args.agent_id,
                provenance=args.provenance,
                dry_run=bool(getattr(args, "dry_run", False)),
            )
            print_json(summary)
            return 0 if summary.get("ok") else 1
        case "intakes":
            summary = list_external_intakes()
            print_json(summary)
            return 0
        case "collection-status":
            summary = collection_status()
            print_json(summary)
            return 0
        case "submitter-package":
            summary = build_submitter_package(args.output)
            print_json(summary)
            return 0 if summary.get("ok") else 1
        case "llm":
            if getattr(args, "report", False):
                if not getattr(args, "submissions", None):
                    print("--report requires --submissions DIR")
                    return 2
                summary = build_evaluation_report(
                    submissions=args.submissions,
                    split=getattr(args, "split", "all"),
                    provenance=getattr(args, "provenance", "any"),
                )
                print_json(summary)
                return 0 if summary.get("dataset_integrity", {}).get("ok") else 1
            summary = run_llm_benchmark(
                submissions=getattr(args, "submissions", None),
                validate_only=bool(getattr(args, "validate_only", False)),
                split=getattr(args, "split", "all"),
            )
        case _:
            return 2
    print_json(summary)
    # governance-style integrity failures are embedded for llm validate
    if summary.get("dataset_integrity") and not summary["dataset_integrity"].get("ok"):
        return 1
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


def _cmd_atlas(args: argparse.Namespace) -> int:
    from authdiff.atlas.crawl import run_crawl
    from authdiff.jsonio import print_json

    if args.atlas_cmd != "crawl":
        return 2
    summary = run_crawl(
        seed_file=args.seed,
        demo_seed=bool(args.demo_seed) or args.seed is None,
        out_dir=args.output_dir,
    )
    print_json(summary)
    return 0 if summary.get("scanned_ok") else 1


def _cmd_lsp_validate(args: argparse.Namespace) -> int:
    from authdiff.jsonio import print_json
    from authdiff.lsp_stub import validate_authority_doc

    diags = validate_authority_doc(args.path)
    print_json({"path": str(args.path), "diagnostics": diags})
    return 1 if any(d.get("severity") == "error" for d in diags) else 0
