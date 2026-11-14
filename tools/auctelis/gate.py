"""Authority gate: base-lock diff + CODEOWNERS + best-effort ruleset check.

Product contract (lock-only): GitHub CODEOWNERS / rulesets enforce human
review. auctelis owns the authority diff:

1. Schema-validate / reject hollow base locks when head has authority
2. Require CODEOWNERS coverage for AUTHORITY.lock (from base ref when provided)
3. On meaningful growth, fail closed unless CODEOWNERS covers the lock; label
   growth vs reduction. Do **not** re-implement PR approval matching — that is
   GitHub's job.
4. Best-effort check that a code-owner-review ruleset (or classic branch
   protection) exists when ``GITHUB_TOKEN`` + repository context are present.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from auctelis.authority_lock import (
    LOCK_NAME,
    build_authority_lock,
    delta_label,
    diff_authority_locks,
)
from auctelis.lock_io import AuthorityLockError, load_authority_lock
from auctelis.security.engine import ScanResult, run_security_scan

# Authority-bearing path globs that CODEOWNERS should cover (docs + ci init).
AUTHORITY_PATH_HINTS = (
    LOCK_NAME,
    ".auctelis.yml",
    "**/.mcp.json",
    "**/.cursor/mcp.json",
    "**/.claude/settings.json",
    "**/hooks.json",
    "**/SKILL.md",
    # Gate self-protection: a hostile PR can edit the Action that enforces the lock.
    ".github/workflows/**",
    ".github/actions/**",
    "CODEOWNERS",
    ".github/CODEOWNERS",
)


def parse_codeowners_for_path(
    codeowners_text: str,
    *,
    target: str = LOCK_NAME,
) -> list[str]:
    """Return owners listed for ``target`` (last matching CODEOWNERS rule wins)."""
    owners: list[str] = []
    for raw in codeowners_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        pattern, *rest = parts
        normalized = pattern.replace("\\", "/").lstrip("/")
        target_norm = target.replace("\\", "/").lstrip("/")
        if (
            normalized in {target_norm, f"**/{target_norm}", f"/{target_norm}"}
            or normalized.endswith(f"/{target_norm}")
            or (normalized == "*" and not owners)
        ):
            owners = [t for t in rest if t.startswith("@")]
    return owners


def load_codeowners_text(root: Path, *, codeowners_path: Path | None = None) -> str:
    if codeowners_path is not None and codeowners_path.is_file():
        return codeowners_path.read_text(encoding="utf-8")
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        path = root / rel
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def load_lock_owners(
    root: Path,
    *,
    codeowners_path: Path | None = None,
    codeowners_text: str | None = None,
) -> list[str]:
    text = (
        codeowners_text
        if codeowners_text is not None
        else load_codeowners_text(root, codeowners_path=codeowners_path)
    )
    if not text:
        return []
    return parse_codeowners_for_path(text)


def codeowners_covers_lock(codeowners_text: str) -> bool:
    return bool(parse_codeowners_for_path(codeowners_text, target=LOCK_NAME))


def _api_get_json(url: str, *, token: str) -> tuple[Any | None, int]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "auctelis-gate",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8")), int(resp.status)
    except urllib.error.HTTPError as exc:
        return None, int(exc.code)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, TypeError):
        return None, 0


def check_code_owner_ruleset(
    *,
    repository: str | None = None,
    token: str | None = None,
    api_base: str | None = None,
    default_branch: str | None = None,
) -> tuple[str, str]:
    """Best-effort: return ``(status, detail)``.

    status is one of ``OK``, ``MISSING``, ``UNVERIFIED``.
    """
    repo = repository or os.environ.get("GITHUB_REPOSITORY")
    tok = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    base = (api_base or os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    if not repo or not tok:
        return "UNVERIFIED", "no GITHUB_REPOSITORY/GITHUB_TOKEN — cannot read rulesets"
    branch = (
        default_branch
        or os.environ.get("GITHUB_BASE_REF")
        or os.environ.get("AUCTELIS_DEFAULT_BRANCH")
    )
    # Rulesets (preferred).
    payload, status = _api_get_json(f"{base}/repos/{repo}/rulesets", token=tok)
    if status in {401, 403}:
        return "UNVERIFIED", f"rulesets API returned HTTP {status} (token scope?)"
    if status == 200 and isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            rules = item.get("rules") or []
            if not isinstance(rules, list):
                # Need detail fetch for full rules.
                rid = item.get("id")
                if rid is None:
                    continue
                detail, dstatus = _api_get_json(f"{base}/repos/{repo}/rulesets/{rid}", token=tok)
                if dstatus != 200 or not isinstance(detail, dict):
                    continue
                rules = detail.get("rules") or []
            for rule in rules if isinstance(rules, list) else []:
                if not isinstance(rule, dict):
                    continue
                if str(rule.get("type") or "") != "pull_request":
                    continue
                params = rule.get("parameters") or {}
                if isinstance(params, dict) and params.get("require_code_owner_review"):
                    return (
                        "OK",
                        f"ruleset {item.get('name') or item.get('id')} requires code-owner review",
                    )
        # Listed rulesets but none require code owners.
        if payload:
            # Fall through to classic protection before declaring MISSING.
            pass
        elif payload == []:
            pass

    # Classic branch protection fallback.
    if not branch:
        meta, mstatus = _api_get_json(f"{base}/repos/{repo}", token=tok)
        if mstatus == 200 and isinstance(meta, dict):
            branch = str(meta.get("default_branch") or "") or None
    if branch:
        prot, pstatus = _api_get_json(
            f"{base}/repos/{repo}/branches/{branch}/protection", token=tok
        )
        if pstatus in {401, 403}:
            return "UNVERIFIED", f"branch protection API returned HTTP {pstatus}"
        if pstatus == 404:
            return "MISSING", f"no branch protection on {branch} and no code-owner ruleset found"
        if pstatus == 200 and isinstance(prot, dict):
            reviews = prot.get("required_pull_request_reviews") or {}
            if isinstance(reviews, dict) and reviews.get("require_code_owner_reviews"):
                return "OK", f"branch protection on {branch} requires code-owner reviews"
            return "MISSING", f"branch protection on {branch} lacks require_code_owner_reviews"
    return "UNVERIFIED", "could not confirm a code-owner-review ruleset"


def growth_label(summary: dict[str, Any]) -> str:
    """Classify lock delta for comments: GROWTH, REDUCTION, or NONE."""
    return delta_label(summary)


def adoption_bootstrap_verdict(
    *,
    base_lock_present: bool,
    head_lock_present: bool,
) -> dict[str, Any]:
    """Distinguish first-lock adoption from a normal growth-gate pass.

    Used by the GitHub Action (and tests) when there is no base-ref lock.
    ``BASELINE_ADOPTED`` is **not** equivalent to ``PASS`` on a growth gate.
    """
    if base_lock_present:
        return {
            "ok": True,
            "ceremony": "growth_gate",
            "verdict": "PASS",
            "message": "Base lock present — run auctelis gate for authority growth.",
        }
    if head_lock_present:
        return {
            "ok": True,
            "ceremony": "baseline_adopted",
            "verdict": "BASELINE_ADOPTED",
            "message": (
                "First AUTHORITY.lock on head with no trusted base lock. "
                "This is a baseline adoption ceremony — require CODEOWNERS review "
                "of the new lock and protection config before merge. "
                "Subsequent PRs must pass the growth gate against this base."
            ),
        }
    return {
        "ok": False,
        "ceremony": "fail_closed",
        "verdict": "FAIL_CLOSED",
        "message": ("locked=true but neither base nor head has AUTHORITY.lock — fail closed."),
    }


def protection_status(ruleset: str | None, *, needs_approval: bool) -> str:
    """Map ruleset probe → review-protection label for reports."""
    if not needs_approval:
        return "n/a"
    status = str(ruleset or "UNVERIFIED").upper()
    if status == "OK":
        return "verified"
    if status == "MISSING":
        return "missing"
    return "unverified"


def run_gate(
    root: Path,
    *,
    base_lock: Path,
    head_lock: Path | None = None,
    scan: ScanResult | None = None,
    repository: str | None = None,
    token: str | None = None,
    codeowners_path: Path | None = None,
    codeowners_text: str | None = None,
    check_ruleset: bool = True,
    strict_ruleset: bool = True,
) -> tuple[dict[str, Any], int]:
    """Compare base→head lock; fail on growth without CODEOWNERS protection.

    ``strict_ruleset`` defaults to True (Authority Watch): UNVERIFIED protection
    on growth is NEEDS_REVIEW, not a green PASS. Pass False for best-effort.
    """
    root = root.resolve()
    try:
        base = load_authority_lock(base_lock)
    except (AuthorityLockError, FileNotFoundError, OSError) as exc:
        return {
            "ok": False,
            "verdict": "FAIL_CLOSED",
            "error": f"cannot read base lock {base_lock}: {exc}",
            "needs_approval": True,
            "required_owners": [],
            "label": "GROWTH",
            "ruleset": "UNVERIFIED",
            "lines": [],
        }, 2
    try:
        if head_lock is not None:
            if not head_lock.is_file():
                return {
                    "ok": False,
                    "verdict": "FAIL_CLOSED",
                    "error": f"head lock not found: {head_lock}",
                    "needs_approval": True,
                    "required_owners": [],
                    "label": "GROWTH",
                    "ruleset": "UNVERIFIED",
                    "lines": [],
                }, 2
            head = load_authority_lock(head_lock)
        else:
            if scan is None:
                scan = run_security_scan(root)
            head = build_authority_lock(root, scan=scan)
    except (AuthorityLockError, FileNotFoundError, OSError) as exc:
        return {
            "ok": False,
            "verdict": "FAIL_CLOSED",
            "error": str(exc),
            "needs_approval": True,
            "required_owners": [],
            "label": "GROWTH",
            "ruleset": "UNVERIFIED",
            "lines": [],
        }, 2
    # Coverage matters even when a trusted head lock is supplied: an unparsed
    # config means the lock's absence of a record is not evidence of no authority.
    if scan is None:
        scan = run_security_scan(root)
    coverage = scan.coverage if isinstance(scan.coverage, dict) else {}
    try:
        unparsed = int(coverage.get("unparsed_agent_config_count") or 0)
    except (TypeError, ValueError):
        unparsed = 0

    base_records = list(base.get("records") or [])
    head_records = list(head.get("records") or [])
    hollow_base = not base_records and not (base.get("mcp_tools") or {})
    if hollow_base and head_records:
        return {
            "ok": False,
            "verdict": "FAIL_CLOSED",
            "error": (
                "hollow base AUTHORITY.lock (no records); refuse to gate growth. "
                "Commit a real lock on the base ref first."
            ),
            "needs_approval": True,
            "required_owners": [],
            "label": "GROWTH",
            "ruleset": "UNVERIFIED",
            "meaningful_authority_change": True,
            "lines": [],
        }, 1

    delta = diff_authority_locks(base, head)
    summary = delta.get("summary") or {}
    meaningful = bool(summary.get("meaningful_authority_change"))
    label = growth_label(summary if isinstance(summary, dict) else {})
    owners = load_lock_owners(
        root, codeowners_path=codeowners_path, codeowners_text=codeowners_text
    )
    co_text = (
        codeowners_text
        if codeowners_text is not None
        else load_codeowners_text(root, codeowners_path=codeowners_path)
    )
    owners_present = codeowners_covers_lock(co_text) if co_text else bool(owners)
    needs_approval = label == "GROWTH"
    ruleset_status, ruleset_detail = "UNVERIFIED", "not checked"
    if check_ruleset and needs_approval:
        ruleset_status, ruleset_detail = check_code_owner_ruleset(
            repository=repository, token=token
        )

    ok = True
    verdict = "PASS"
    error: str | None = None
    if needs_approval and not owners_present:
        ok = False
        verdict = "NEEDS_REVIEW"
        error = (
            "AUTHORITY.lock has no CODEOWNERS entry on the trusted ref; "
            "cannot rely on GitHub-native review. "
            "Run `auctelis ci init --owner @user` and protect authority paths."
        )
    elif needs_approval and ruleset_status == "MISSING":
        ok = False
        verdict = "NEEDS_REVIEW"
        error = (
            "Authority grew but no code-owner-review ruleset/branch protection "
            f"was found ({ruleset_detail}). Enable require_code_owner_review, "
            "then merge the lock diff under CODEOWNERS."
        )
    elif needs_approval and ruleset_status == "UNVERIFIED" and strict_ruleset and check_ruleset:
        # Strict only applies when the ruleset probe actually ran. --skip-ruleset-check
        # is best-effort labeling (CODEOWNERS still required).
        ok = False
        verdict = "NEEDS_REVIEW"
        error = (
            "Authority grew but ruleset check is UNVERIFIED under --strict-ruleset "
            f"({ruleset_detail}). Provide API access, enable code-owner review, "
            "or pass --no-strict-ruleset for best-effort mode."
        )
    elif needs_approval:
        # CODEOWNERS present; ruleset OK or UNVERIFIED (best-effort unless strict).
        # Growth is labeled for humans — GitHub enforces the actual review.
        ok = True
        verdict = "PASS"
        if ruleset_status == "UNVERIFIED" and check_ruleset:
            error = (
                f"PASS / protection unverified — ruleset check UNVERIFIED "
                f"({ruleset_detail}). Confirm a code-owner-review ruleset is enabled."
            )
        elif ruleset_status == "UNVERIFIED" and not check_ruleset:
            error = (
                "PASS / ruleset check skipped — growth labeled; confirm CODEOWNERS "
                "review is required in branch protection."
            )

    # Unparsed configs mean authority could not be established. Never let a
    # missing record look like a reduction/PASS.
    if unparsed:
        ok = False
        verdict = "NEEDS_REVIEW"
        detail = f"{unparsed} agent config file(s) could not be parsed on head"
        error = f"{error} {detail}." if error else f"{detail} — review before merge."

    protection = protection_status(ruleset_status, needs_approval=needs_approval)
    report: dict[str, Any] = {
        "ok": ok,
        "verdict": verdict,
        "ceremony": "growth_gate",
        "protection": protection,
        "strict_ruleset": strict_ruleset,
        "meaningful_authority_change": meaningful,
        "needs_approval": needs_approval,
        "label": label,
        "required_owners": owners,
        "owners_present": owners_present,
        "ruleset": ruleset_status,
        "ruleset_detail": ruleset_detail,
        "delta": delta,
        "lines": delta.get("lines") or [],
        "authority_path_hints": list(AUTHORITY_PATH_HINTS),
    }
    if error:
        report["error"] = error
    return report, 0 if ok else 1


def render_gate_report(report: dict[str, Any]) -> str:
    verdict = str(report.get("verdict") or "UNKNOWN")
    protection = str(report.get("protection") or "")
    if verdict == "PASS" and protection == "verified":
        header = "auctelis gate — PASS / protection verified"
    elif verdict == "PASS" and protection == "unverified":
        header = "auctelis gate — PASS / protection unverified"
    elif verdict == "BASELINE_ADOPTED":
        header = "auctelis gate — BASELINE_ADOPTED (adoption ceremony, not growth PASS)"
    else:
        header = f"auctelis gate — {verdict}"
    lines = [header]
    label = str(report.get("label") or "NONE")
    if report.get("ceremony") == "baseline_adopted":
        lines.append("Ceremony: baseline adoption (first lock; not a growth-gate pass)")
    lines.append(f"Authority delta: {label}")
    if report.get("needs_approval"):
        owners = ", ".join(report.get("required_owners") or []) or "(none)"
        lines.append(f"CODEOWNERS for AUTHORITY.lock: {owners}")
        ruleset_line = (
            f"Ruleset: {report.get('ruleset')} — {report.get('ruleset_detail') or ''}"
        ).rstrip(" —")
        if protection:
            ruleset_line += f" [{protection}]"
        lines.append(ruleset_line)
        if report.get("strict_ruleset"):
            lines.append("Strict ruleset: ON (UNVERIFIED fails growth)")
        lines.append(
            "Approval model: GitHub-native CODEOWNERS/rulesets "
            "(auctelis labels growth; it does not count PR reviews)."
        )
    for line in report.get("lines") or []:
        lines.append(f"  {line}")
    if report.get("error"):
        lines.append(str(report["error"]))
    if report.get("message") and report.get("ceremony") == "baseline_adopted":
        lines.append(str(report["message"]))
    if report.get("ok") and label == "REDUCTION":
        lines.append("Authority reduced vs base lock — no extra review required.")
    elif report.get("ok") and not report.get("needs_approval"):
        lines.append("No authority addition/expansion vs base lock.")
    return "\n".join(lines)
