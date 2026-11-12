"""Authority gate: base-lock diff + CODEOWNERS + best-effort ruleset check.

Product contract (lock-only): GitHub CODEOWNERS / rulesets enforce human
review. authdiff owns the authority diff:

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

from authdiff.authority_lock import LOCK_NAME, build_authority_lock, diff_authority_locks
from authdiff.lock_io import AuthorityLockError, load_authority_lock
from authdiff.security.engine import ScanResult, run_security_scan

# Authority-bearing path globs that CODEOWNERS should cover (docs + ci init).
AUTHORITY_PATH_HINTS = (
    LOCK_NAME,
    ".authdiff.yml",
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
            "User-Agent": "authdiff-gate",
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
        or os.environ.get("AUTHDIFF_DEFAULT_BRANCH")
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
    adds = int(summary.get("additions") or 0)
    expansions = int(summary.get("expansions") or 0)
    replacements = int(summary.get("replacements") or 0)
    policy = bool(summary.get("policy_changed"))
    reductions = int(summary.get("reductions") or 0) + int(summary.get("removals") or 0)
    if adds or expansions or replacements or policy:
        return "GROWTH"
    if reductions:
        return "REDUCTION"
    return "NONE"


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
) -> tuple[dict[str, Any], int]:
    """Compare base→head lock; fail on growth without CODEOWNERS protection."""
    root = root.resolve()
    try:
        base = load_authority_lock(base_lock)
    except AuthorityLockError as exc:
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
    try:
        if head_lock is not None and head_lock.is_file():
            head = load_authority_lock(head_lock)
        else:
            if scan is None:
                scan = run_security_scan(root)
            head = build_authority_lock(root, scan=scan)
    except AuthorityLockError as exc:
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
            "Run `authdiff ci init --owner @user` and protect authority paths."
        )
    elif needs_approval and ruleset_status == "MISSING":
        ok = False
        verdict = "NEEDS_REVIEW"
        error = (
            "Authority grew but no code-owner-review ruleset/branch protection "
            f"was found ({ruleset_detail}). Enable require_code_owner_review, "
            "then merge the lock diff under CODEOWNERS."
        )
    elif needs_approval:
        # CODEOWNERS present; ruleset OK or UNVERIFIED (best-effort). Growth is
        # labeled for humans — GitHub enforces the actual review.
        ok = True
        verdict = "PASS"
        if ruleset_status == "UNVERIFIED":
            error = (
                f"Authority growth labeled; ruleset check UNVERIFIED ({ruleset_detail}). "
                "Confirm a code-owner-review ruleset is enabled."
            )

    report: dict[str, Any] = {
        "ok": ok,
        "verdict": verdict,
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
    lines = [f"authdiff gate — {report.get('verdict')}"]
    label = str(report.get("label") or "NONE")
    lines.append(f"Authority delta: {label}")
    if report.get("needs_approval"):
        owners = ", ".join(report.get("required_owners") or []) or "(none)"
        lines.append(f"CODEOWNERS for AUTHORITY.lock: {owners}")
        lines.append(
            f"Ruleset: {report.get('ruleset')} — {report.get('ruleset_detail') or ''}".rstrip(" —")
        )
        lines.append(
            "Approval model: GitHub-native CODEOWNERS/rulesets "
            "(authdiff labels growth; it does not count PR reviews)."
        )
    for line in report.get("lines") or []:
        lines.append(f"  {line}")
    if report.get("error"):
        lines.append(str(report["error"]))
    if report.get("ok") and label == "REDUCTION":
        lines.append("Authority reduced vs base lock — no extra review required.")
    elif report.get("ok") and not report.get("needs_approval"):
        lines.append("No authority addition/expansion vs base lock.")
    return "\n".join(lines)
