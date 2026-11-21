"""Maintainer-only CLI handlers (``auctelis-dev``).

The product CLI (``auctelis``) lives in :mod:`auctelis.cli.dispatch`: ``check``,
``diff``, ``gate``, ``init``, ``lock``, ``status``, ``trust``, ``why``, ``demo``,
and the ``ci`` alias. Everything here is a maintainer / research surface and is
not part of the Authority Diff gate path.

Keeping these handlers out of ``dispatch`` keeps the product command surface
small and reviewable, and makes the research boundary explicit: every handler
that needs ``auctelis_research`` calls :func:`require_research`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from auctelis.authority_lock import (
    build_authority_lock,
    check_locked,
    diff_authority_locks,
)
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.gate import load_lock_owners
from auctelis.hosts.profiles import get_host_profile, list_host_profiles
from auctelis.inventory.collector import collect_inventory, inventory_to_json
from auctelis.jsonio import print_json, read_json, write_json, write_text
from auctelis.lock_io import load_authority_lock
from auctelis.policy import apply_policy_defaults, discover_policy_file, load_policy
from auctelis.supply_chain.digest import sha256_file, verify_file_digest
from auctelis_devtools.export.agent_digest import render_agent_digest
from auctelis_devtools.export.sarif import report_to_sarif
from auctelis_devtools.validate_report import validate_report_file


def require_research() -> None:
    """Research scanner lives outside the product wheel (source / editable only)."""
    from auctelis.cli.guards import require_research as _require

    _require()


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


def cmd_scan(args: argparse.Namespace) -> int:
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

    require_research()
    from auctelis_research.scan import run_scan

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


def cmd_build(args: argparse.Namespace) -> int:
    from auctelis_devtools.build import (
        build_all,
        check_pypi_cutover_readiness,
        sync_schemas,
    )

    match args.target:
        case "schemas":
            for line in sync_schemas():
                print(line)
        case "pypi-check":
            for line in check_pypi_cutover_readiness():
                print(line)
        case _:
            print_json(build_all())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    semantic = not getattr(args, "no_semantic", False)
    if args.validate_cmd != "report":
        return 2
    report_result = validate_report_file(args.path, semantic=semantic)
    return _print_validation(args.path, ok=report_result.ok, issues=report_result.issues)


def cmd_inventory(args: argparse.Namespace) -> int:
    result = collect_inventory(args.path)
    return _write_or_print(inventory_to_json(result), args.output)


def cmd_verify(args: argparse.Namespace) -> int:
    if args.verify_cmd != "digest":
        return 2
    if args.expected:
        ok, actual = verify_file_digest(args.path, args.expected)
        print_json({"ok": ok, "sha256": actual})
        return 0 if ok else 1
    print_json({"sha256": sha256_file(args.path)})
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    if args.export_cmd != "sarif":
        return 2
    if not args.report.is_file():
        print(f"Report not found: {args.report}")
        return 1
    sarif_doc = report_to_sarif(read_json(args.report))
    if args.output:
        write_json(args.output, sarif_doc)
        count = len(sarif_doc["runs"][0]["results"])
        print(f"Wrote {args.output} ({count} results)")
    else:
        print_json(sarif_doc)
    return 0


def cmd_annotate(args: argparse.Namespace) -> int:
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
        require_research()
        from auctelis_research.annotate import render_text_annotations

        text = render_text_annotations(doc)
    else:
        require_research()
        from auctelis_research.annotate import render_github_annotations

        text = render_github_annotations(doc)
    if text:
        print(text, end="" if text.endswith("\n") else "\n")
    else:
        print("No SECURITY_FINDING/EXPOSURE annotations.")
    return 0


def cmd_hosts(args: argparse.Namespace) -> int:
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


def cmd_corpus() -> int:
    require_research()
    from auctelis_research.corpus.runner import run_corpus

    summary = run_corpus()
    print_json(summary)
    return 0 if summary.get("failed", 0) == 0 else 1


def cmd_deps(args: argparse.Namespace) -> int:
    from auctelis_devtools.deps import outdated_report, upgrade_pins

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


def cmd_lint(args: argparse.Namespace) -> int:
    from auctelis_devtools.lint import run_ruff

    summary = run_ruff(
        fix=args.fix,
        format_code=args.format_code,
        check_format=args.check_format and not args.format_code,
    )
    return 0 if summary.get("ok") else 1


def cmd_run(args: argparse.Namespace) -> int:
    require_research()
    from auctelis_research.broker import run_brokered

    # ``run_command`` is separate from the subparser dest so the subcommand name
    # is not overwritten by REMAINDER (regression: ``auctelis-dev run`` exited 2).
    cmd = list(getattr(args, "run_command", None) or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("usage: auctelis run [--lock AUTHORITY.lock] -- <command…>")
        return 2
    return run_brokered(cmd, lock_path=args.lock)


def cmd_snapshot(args: argparse.Namespace) -> int:
    require_research()
    from auctelis_research.mcp_snapshot import snapshot_execute, snapshot_from_file

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


def cmd_artifact_vet(args: argparse.Namespace) -> int:
    require_research()
    from auctelis_research.artifact_vet import run_artifact_vet, write_artifact_report

    report = run_artifact_vet(args.spec)
    if args.output:
        write_artifact_report(report, args.output)
        print(f"Wrote {args.output}")
    print_json(report.to_dict())
    return 0 if report.verdict == "ALLOW_WITH_GAPS" else 1
