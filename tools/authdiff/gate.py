"""Authority gate: base-lock diff + CODEOWNERS presence + GitHub-native approval.

Product contract: authority growth fails until a PR is approved under GitHub
CODEOWNERS/rulesets. This module no longer matches individual logins to
``@org/team`` owners — that is GitHub's job. We only:

1. Schema-validate / reject hollow base locks when head has authority
2. Require CODEOWNERS coverage for AUTHORITY.lock (from base ref when provided)
3. On meaningful growth, require at least one APPROVED PR review (or
   ``--approved-by`` for local harnesses)
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


def _normalize_owner(value: str) -> str:
    text = value.strip()
    if text.startswith("@"):
        return text.lower()
    return f"@{text}".lower()


def fetch_pr_approving_logins(
    *,
    repository: str,
    pr_number: int,
    token: str,
    api_base: str = "https://api.github.com",
) -> list[str]:
    """Return logins of users with an *approved* review on the PR."""
    url = f"{api_base.rstrip('/')}/repos/{repository}/pulls/{pr_number}/reviews"
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
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    latest: dict[str, str] = {}
    for review in payload:
        if not isinstance(review, dict):
            continue
        user = review.get("user") or {}
        login = str(user.get("login") or "").strip()
        state = str(review.get("state") or "").upper()
        if not login:
            continue
        latest[login.lower()] = state
    return [_normalize_owner(login) for login, state in latest.items() if state == "APPROVED"]


def resolve_approvers(
    *,
    approved_by: list[str] | None = None,
    repository: str | None = None,
    pr_number: int | None = None,
    token: str | None = None,
    api_base: str | None = None,
) -> list[str]:
    """Collect GitHub PR approvals and explicit ``--approved-by`` harness overrides."""
    found = [_normalize_owner(x) for x in (approved_by or []) if x and x.strip()]
    repo = repository or os.environ.get("GITHUB_REPOSITORY")
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    pr = pr_number
    if pr is None:
        raw = os.environ.get("AUTHDIFF_PR_NUMBER") or os.environ.get("GITHUB_PR_NUMBER")
        if not raw:
            event_path = os.environ.get("GITHUB_EVENT_PATH")
            if event_path and Path(event_path).is_file():
                try:
                    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
                    raw = str((event.get("pull_request") or {}).get("number") or "")
                except (OSError, json.JSONDecodeError, TypeError):
                    raw = ""
        if raw and raw.isdigit():
            pr = int(raw)
    if repo and pr and token:
        found.extend(
            fetch_pr_approving_logins(
                repository=repo,
                pr_number=pr,
                token=token,
                api_base=api_base or os.environ.get("GITHUB_API_URL") or "https://api.github.com",
            )
        )
    out: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def github_native_approval_present(*, approvers: list[str]) -> bool:
    """True when GitHub (or a harness) has recorded at least one approval.

    CODEOWNERS/rulesets decide *who* may approve; authdiff only checks that an
    approval exists once owners are configured on the base ref.
    """
    return bool(approvers)


def run_gate(
    root: Path,
    *,
    base_lock: Path,
    head_lock: Path | None = None,
    scan: ScanResult | None = None,
    approved_by: list[str] | None = None,
    repository: str | None = None,
    pr_number: int | None = None,
    token: str | None = None,
    codeowners_path: Path | None = None,
    codeowners_text: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Compare base→head lock; fail on growth without GitHub-native approval."""
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
            "approvers": [],
            "approved": False,
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
            "approvers": [],
            "approved": False,
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
            "approvers": [],
            "approved": False,
            "meaningful_authority_change": True,
            "lines": [],
        }, 1

    delta = diff_authority_locks(base, head)
    summary = delta.get("summary") or {}
    meaningful = bool(summary.get("meaningful_authority_change"))
    owners = load_lock_owners(
        root, codeowners_path=codeowners_path, codeowners_text=codeowners_text
    )
    co_text = (
        codeowners_text
        if codeowners_text is not None
        else load_codeowners_text(root, codeowners_path=codeowners_path)
    )
    owners_present = codeowners_covers_lock(co_text) if co_text else bool(owners)
    approvers = resolve_approvers(
        approved_by=approved_by,
        repository=repository,
        pr_number=pr_number,
        token=token,
    )
    approved = github_native_approval_present(approvers=approvers)
    needs_approval = meaningful and bool(
        int(summary.get("additions") or 0)
        or int(summary.get("expansions") or 0)
        or int(summary.get("replacements") or 0)
        or summary.get("policy_changed")
    )
    ok = (not needs_approval) or (owners_present and approved)
    report: dict[str, Any] = {
        "ok": ok,
        "verdict": "PASS" if ok else "NEEDS_APPROVAL",
        "meaningful_authority_change": meaningful,
        "needs_approval": needs_approval,
        "required_owners": owners,
        "owners_present": owners_present,
        "approvers": approvers,
        "approved": approved,
        "delta": delta,
        "lines": delta.get("lines") or [],
        "authority_path_hints": list(AUTHORITY_PATH_HINTS),
    }
    if needs_approval and not owners_present:
        report["error"] = (
            "AUTHORITY.lock has no CODEOWNERS entry on the trusted ref; "
            "cannot rely on GitHub-native approval. "
            "Run `authdiff ci init --owner @user` and protect authority paths."
        )
        report["ok"] = False
        report["verdict"] = "NEEDS_APPROVAL"
        return report, 1
    return report, 0 if ok else 1


def render_gate_report(report: dict[str, Any]) -> str:
    lines = [f"authdiff gate — {report.get('verdict')}"]
    if report.get("needs_approval"):
        owners = ", ".join(report.get("required_owners") or []) or "(none)"
        lines.append(f"CODEOWNERS for AUTHORITY.lock: {owners}")
        lines.append(
            "Approval model: GitHub-native CODEOWNERS/rulesets "
            "(any APPROVED review counts once owners are configured)."
        )
        approvers = ", ".join(report.get("approvers") or []) or "(none yet)"
        lines.append(f"Approvers seen: {approvers}")
    for line in report.get("lines") or []:
        lines.append(f"  {line}")
    if report.get("error"):
        lines.append(str(report["error"]))
    if report.get("ok") and not report.get("needs_approval"):
        lines.append("No unapproved authority addition/expansion vs base lock.")
    return "\n".join(lines)
