"""Authority gate: base-lock diff + trusted CODEOWNER approval.

Product contract: no addition/expansion reaches green until a CODEOWNERS
reviewer for ``AUTHORITY.lock`` has approved the change. Approvals are
*read* from GitHub PR reviews (or an explicit ``--approved-by`` override for
local/CI harnesses) — the write-only ``approvals[]`` array on the lock is
not consulted.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from authdiff.authority_lock import LOCK_NAME, build_authority_lock, diff_authority_locks
from authdiff.lock_io import load_authority_lock
from authdiff.security.engine import ScanResult, run_security_scan


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
        # Simple basename / exact / trailing match — enough for AUTHORITY.lock.
        normalized = pattern.replace("\\", "/").lstrip("/")
        target_norm = target.replace("\\", "/").lstrip("/")
        if (
            normalized in {target_norm, f"**/{target_norm}", f"/{target_norm}"}
            or normalized.endswith(f"/{target_norm}")
            or (normalized == "*" and not owners)
        ):
            owners = [t for t in rest if t.startswith("@")]
    return owners


def load_lock_owners(root: Path) -> list[str]:
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        path = root / rel
        if path.is_file():
            return parse_codeowners_for_path(path.read_text(encoding="utf-8"))
    return []


def _normalize_owner(value: str) -> str:
    text = value.strip()
    if text.startswith("@"):
        return text.lower()
    return f"@{text}".lower()


def _login_to_owner(login: str) -> str:
    return _normalize_owner(login)


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
    # Last review per user wins.
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
    return [_login_to_owner(login) for login, state in latest.items() if state == "APPROVED"]


def resolve_approvers(
    *,
    approved_by: list[str] | None = None,
    repository: str | None = None,
    pr_number: int | None = None,
    token: str | None = None,
    api_base: str | None = None,
) -> list[str]:
    """Merge explicit ``--approved-by`` with GitHub PR approvals when available."""
    found = [_normalize_owner(x) for x in (approved_by or []) if x and x.strip()]
    repo = repository or os.environ.get("GITHUB_REPOSITORY")
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    pr = pr_number
    if pr is None:
        raw = os.environ.get("AUTHDIFF_PR_NUMBER") or os.environ.get("GITHUB_PR_NUMBER")
        if not raw:
            # actions/github-script style event path
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
    # Dedupe preserving order.
    out: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def trusted_approval_present(
    *,
    required_owners: list[str],
    approvers: list[str],
) -> bool:
    if not required_owners:
        # No CODEOWNERS → cannot establish trust; treat as unapproved.
        return False
    required = {_normalize_owner(o) for o in required_owners}
    have = {_normalize_owner(a) for a in approvers}
    # Team owners (@org/team) cannot be matched to a user login without GraphQL;
    # accept exact match, or user login when owner is a bare @user.
    if required & have:
        return True
    # If only team owners are listed, require an explicit --approved-by that
    # matches the team slug exactly (operators can pass @org/team in harnesses).
    return bool(required & have)


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
) -> tuple[dict[str, Any], int]:
    """Compare base→head lock; fail on meaningful growth without trusted approval."""
    root = root.resolve()
    base = load_authority_lock(base_lock)
    if head_lock is not None and head_lock.is_file():
        head = load_authority_lock(head_lock)
    else:
        if scan is None:
            scan = run_security_scan(root)
        head = build_authority_lock(root, scan=scan)
    delta = diff_authority_locks(base, head)
    summary = delta.get("summary") or {}
    meaningful = bool(summary.get("meaningful_authority_change"))
    owners = load_lock_owners(root)
    approvers = resolve_approvers(
        approved_by=approved_by,
        repository=repository,
        pr_number=pr_number,
        token=token,
    )
    approved = trusted_approval_present(required_owners=owners, approvers=approvers)
    needs_approval = meaningful and bool(
        int(summary.get("additions") or 0)
        or int(summary.get("expansions") or 0)
        or int(summary.get("replacements") or 0)
        or summary.get("policy_changed")
    )
    ok = (not needs_approval) or approved
    report: dict[str, Any] = {
        "ok": ok,
        "verdict": "PASS" if ok else "NEEDS_APPROVAL",
        "meaningful_authority_change": meaningful,
        "needs_approval": needs_approval,
        "required_owners": owners,
        "approvers": approvers,
        "approved": approved,
        "delta": delta,
        "lines": delta.get("lines") or [],
    }
    if not owners and needs_approval:
        report["error"] = (
            "AUTHORITY.lock has no CODEOWNERS entry; cannot verify a trusted approver. "
            "Run `authdiff ci init --owner @team`."
        )
    return report, 0 if ok else 1


def render_gate_report(report: dict[str, Any]) -> str:
    lines = [f"authdiff gate — {report.get('verdict')}"]
    if report.get("needs_approval"):
        owners = ", ".join(report.get("required_owners") or []) or "(none)"
        lines.append(f"Needs approval from: {owners}")
        approvers = ", ".join(report.get("approvers") or []) or "(none yet)"
        lines.append(f"Approvers seen: {approvers}")
    for line in report.get("lines") or []:
        lines.append(f"  {line}")
    if report.get("error"):
        lines.append(str(report["error"]))
    if report.get("ok") and not report.get("needs_approval"):
        lines.append("No unapproved authority addition/expansion vs base lock.")
    return "\n".join(lines)
