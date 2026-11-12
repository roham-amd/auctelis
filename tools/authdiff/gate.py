"""Authority gate: base-lock diff + CODEOWNERS presence + GitHub-native approval.

Product contract: authority growth fails until a PR is approved under GitHub
CODEOWNERS/rulesets. This module:

1. Schema-validate / reject hollow base locks when head has authority
2. Require CODEOWNERS coverage for AUTHORITY.lock (from base ref when provided)
3. On meaningful growth, require at least one APPROVED PR review on the PR head
   commit (paginated). User owners in CODEOWNERS must intersect approvers;
   team-only CODEOWNERS are marked ``approval_enforcement: UNVERIFIED`` because
   GitHub team expansion is ruleset territory.
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


def _is_team_owner(owner: str) -> bool:
    """GitHub team refs look like ``@org/team``; user logins have no slash."""
    return "/" in _normalize_owner(owner).lstrip("@")


def resolve_head_sha(*, head_sha: str | None = None) -> str | None:
    """Best-effort PR head SHA from args / Actions env / event payload."""
    if head_sha and head_sha.strip():
        return head_sha.strip().lower()
    for key in ("AUTHDIFF_HEAD_SHA", "GITHUB_SHA"):
        raw = os.environ.get(key)
        if raw and raw.strip():
            return raw.strip().lower()
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).is_file():
        try:
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            pr = event.get("pull_request") or {}
            sha = str((pr.get("head") or {}).get("sha") or "").strip()
            if sha:
                return sha.lower()
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return None


def _parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        piece = part.strip()
        if 'rel="next"' not in piece:
            continue
        if piece.startswith("<") and ">" in piece:
            return piece[1 : piece.index(">")]
    return None


def fetch_pr_approving_logins(
    *,
    repository: str,
    pr_number: int,
    token: str,
    api_base: str = "https://api.github.com",
    head_sha: str | None = None,
) -> list[str]:
    """Return logins with an APPROVED review on ``head_sha`` (paginated).

    When ``head_sha`` is set, stale approvals on older commits are ignored.
    """
    url: str | None = (
        f"{api_base.rstrip('/')}/repos/{repository}/pulls/{pr_number}/reviews?per_page=100"
    )
    latest: dict[str, dict[str, str]] = {}
    pages = 0
    while url and pages < 20:
        pages += 1
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
                link = resp.headers.get("Link")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            break
        if not isinstance(payload, list):
            break
        for review in payload:
            if not isinstance(review, dict):
                continue
            user = review.get("user") or {}
            login = str(user.get("login") or "").strip()
            state = str(review.get("state") or "").upper()
            commit_id = str(review.get("commit_id") or "").strip().lower()
            if not login:
                continue
            latest[login.lower()] = {"state": state, "commit_id": commit_id}
        url = _parse_link_next(link)

    required = (head_sha or "").strip().lower()
    out: list[str] = []
    for login, meta in latest.items():
        if meta.get("state") != "APPROVED":
            continue
        commit_id = meta.get("commit_id") or ""
        if (
            required
            and commit_id
            and not (
                commit_id == required
                or commit_id.startswith(required)
                or required.startswith(commit_id)
            )
        ):
            continue
        if required and not commit_id:
            # Missing commit_id cannot prove the approval covers head.
            continue
        out.append(_normalize_owner(login))
    return out


def resolve_approvers(
    *,
    approved_by: list[str] | None = None,
    repository: str | None = None,
    pr_number: int | None = None,
    token: str | None = None,
    api_base: str | None = None,
    head_sha: str | None = None,
) -> list[str]:
    """Collect GitHub PR approvals and explicit ``--approved-by`` harness overrides."""
    found = [_normalize_owner(x) for x in (approved_by or []) if x and x.strip()]
    repo = repository or os.environ.get("GITHUB_REPOSITORY")
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    sha = resolve_head_sha(head_sha=head_sha)
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
                head_sha=sha,
            )
        )
    out: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def evaluate_approval(
    *,
    owners: list[str],
    approvers: list[str],
) -> tuple[bool, str]:
    """Return ``(approved, enforcement)``.

    - User owners present: require intersection with approvers → ``OWNER_MATCHED``.
    - Only team owners: any APPROVED review counts, but enforcement is
      ``UNVERIFIED`` (GitHub rulesets must enforce team membership).
    - Mixed: prefer user intersection when any user owner matched; else UNVERIFIED
      if a team owner exists and any approval is present.
    """
    if not approvers:
        return False, "NO_APPROVAL"
    normalized_owners = [_normalize_owner(o) for o in owners]
    user_owners = [o for o in normalized_owners if not _is_team_owner(o)]
    team_owners = [o for o in normalized_owners if _is_team_owner(o)]
    approver_set = {_normalize_owner(a) for a in approvers}
    if user_owners:
        matched = sorted(approver_set.intersection(user_owners))
        if matched:
            return True, "OWNER_MATCHED"
        if team_owners:
            return True, "UNVERIFIED"
        return False, "OWNER_MISMATCH"
    if team_owners:
        return True, "UNVERIFIED"
    # CODEOWNERS present but empty owner parse — treat as unverified presence.
    return True, "UNVERIFIED"


def github_native_approval_present(*, approvers: list[str]) -> bool:
    """True when GitHub (or a harness) has recorded at least one approval."""
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
    head_sha: str | None = None,
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
            "approval_enforcement": "FAIL_CLOSED",
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
            "approval_enforcement": "FAIL_CLOSED",
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
            "approval_enforcement": "FAIL_CLOSED",
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
        head_sha=head_sha,
    )
    needs_approval = meaningful and bool(
        int(summary.get("additions") or 0)
        or int(summary.get("expansions") or 0)
        or int(summary.get("replacements") or 0)
        or summary.get("policy_changed")
    )
    approved = False
    enforcement = "NOT_REQUIRED"
    if needs_approval:
        approved, enforcement = evaluate_approval(owners=owners, approvers=approvers)
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
        "approval_enforcement": enforcement,
        "head_sha": resolve_head_sha(head_sha=head_sha),
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
        report["approval_enforcement"] = "NO_CODEOWNERS"
        return report, 1
    if needs_approval and enforcement == "OWNER_MISMATCH":
        report["error"] = (
            "PR approvals do not include a CODEOWNERS user for AUTHORITY.lock. "
            "Required: "
            + (", ".join(owners) or "(none)")
            + ". Approvers seen: "
            + (", ".join(approvers) or "(none)")
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
        enforcement = str(report.get("approval_enforcement") or "")
        if enforcement == "UNVERIFIED":
            lines.append(
                "Approval enforcement: UNVERIFIED "
                "(team CODEOWNERS — enable GitHub rulesets for code-owner review)."
            )
        elif enforcement == "OWNER_MATCHED":
            lines.append("Approval enforcement: OWNER_MATCHED (user owner approved head).")
        else:
            lines.append(
                "Approval model: GitHub-native CODEOWNERS/rulesets; "
                "approvals must cover the PR head commit."
            )
        approvers = ", ".join(report.get("approvers") or []) or "(none yet)"
        lines.append(f"Approvers seen: {approvers}")
        if report.get("head_sha"):
            lines.append(f"Head SHA filter: {report['head_sha'][:12]}")
    for line in report.get("lines") or []:
        lines.append(f"  {line}")
    if report.get("error"):
        lines.append(str(report["error"]))
    if report.get("ok") and not report.get("needs_approval"):
        lines.append("No unapproved authority addition/expansion vs base lock.")
    return "\n".join(lines)
