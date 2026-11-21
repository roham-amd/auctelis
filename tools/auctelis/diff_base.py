"""Local PR Authority Diff simulator — ``auctelis diff --base <ref>``.

Always extract base authority from a temporary detached worktree first
(tree-truth), matching the lockless PR Action path. Fall back to a committed
``AUTHORITY.lock`` on the base ref only when worktree extract fails. When both
succeed and disagree, surface ``base_lock_drift`` so local pre-push stays honest.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from auctelis.authority_lock import (
    LOCK_NAME,
    build_authority_lock,
    delta_label,
    diff_authority_locks,
)
from auctelis.check import SCHEMA_VERSION, attach_launcher_args, attach_launcher_args_to_delta
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.lock_io import AuthorityLockError, empty_authority_lock, load_authority_lock
from auctelis.reach_tiers import load_trusted_hosts
from auctelis.security.engine import run_authority_inventory

_GIT = shutil.which("git")


def _git(
    repo: Path,
    *args: str,
) -> subprocess.CompletedProcess[str] | None:
    if not _GIT:
        return None
    try:
        # Fixed git argv, no shell, repo path passed as a separate argument.
        return subprocess.run(  # nosec B603
            [_GIT, "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None


def _git_show(repo: Path, ref: str, relpath: str) -> str | None:
    proc = _git(repo, "show", f"{ref}:{relpath}")
    if proc is None or proc.returncode != 0:
        return None
    return proc.stdout


def _git_ref_valid(repo: Path, ref: str) -> bool:
    """True only when the ref resolves to a commit (not merely 'some ref')."""
    proc = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return proc is not None and proc.returncode == 0


def _git_has_file(repo: Path, ref: str, relpath: str) -> bool:
    proc = _git(repo, "cat-file", "-e", f"{ref}:{relpath}")
    return proc is not None and proc.returncode == 0


def _extract_tree_authority(repo: Path, base_ref: str) -> dict[str, Any] | None:
    """Build an AUTHORITY.lock-shaped dict from ``base_ref`` via detached worktree."""
    tmp = tempfile.mkdtemp(prefix="auctelis-diff-wt-")
    work = Path(tmp) / "wt"
    try:
        proc = _git(repo, "worktree", "add", "--detach", str(work), base_ref)
        if proc is None or proc.returncode != 0:
            return None
        try:
            scan = run_authority_inventory(work)
            return build_authority_lock(work, scan=scan)
        finally:
            _git(repo, "worktree", "remove", "--force", str(work))
    except (OSError, AuthorityLockError, ValueError):
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _load_committed_base_lock(
    repo: Path,
    base_ref: str,
    lock_name: str,
) -> dict[str, Any] | None:
    """Return the committed base lock, or ``None`` if missing / unusable."""
    if not _git_has_file(repo, base_ref, lock_name):
        return None
    raw = _git_show(repo, base_ref, lock_name)
    if raw is None:
        return None
    with tempfile.TemporaryDirectory(prefix="auctelis-diff-base-") as tmp:
        base_path = Path(tmp) / lock_name
        base_path.write_text(raw, encoding="utf-8")
        try:
            return load_authority_lock(base_path)
        except (AuthorityLockError, OSError):
            return None


def run_diff_base(
    root: Path,
    *,
    base_ref: str,
    lock_name: str = LOCK_NAME,
) -> tuple[str, dict[str, Any], int]:
    """Return ``(text, payload, exit_code)`` for a local base-ref diff.

    Exit codes mirror gate: 0 quiet/none, 1 needs review / growth, 2 fail-closed.
    """
    repo = root.expanduser().resolve()
    if not _git_ref_valid(repo, base_ref):
        payload = {
            "schema_version": SCHEMA_VERSION,
            "verdict": "FAIL_CLOSED",
            "error": f"unknown git ref {base_ref!r} (git rev-parse --verify {base_ref}^{{commit}})",
            "base_ref": base_ref,
            "baseline_state": "invalid_ref",
        }
        return f"auctelis diff --base: {payload['error']}", payload, 2

    # Tree-truth first (Action parity). Committed lock is a fallback / drift signal.
    extracted = _extract_tree_authority(repo, base_ref)
    committed = _load_committed_base_lock(repo, base_ref, lock_name)
    base_lock_drift = False
    baseline_state: str
    base: dict[str, Any]

    if extracted is not None:
        baseline_state = "tree"
        base = extracted
        if committed is not None:
            drift_delta = diff_authority_locks(committed, extracted)
            drift_summary = drift_delta.get("summary") or {}
            if bool(drift_summary.get("authority_changed")):
                base_lock_drift = True
    elif committed is not None:
        baseline_state = "present"
        base = committed
    else:
        baseline_state = "absent"
        base = empty_authority_lock()

    trusted_hosts = load_trusted_hosts(repo)
    scan = run_authority_inventory(repo)
    head = build_authority_lock(repo, scan=scan)
    head_records = list(head.get("records") or [])
    attach_launcher_args(head_records, scan)
    delta = diff_authority_locks(base, head, trusted_hosts=trusted_hosts)
    attach_launcher_args_to_delta(delta, head_records)
    summary = dict(delta.get("summary") or {})
    label = delta_label(summary)
    coverage = scan.coverage if isinstance(scan.coverage, dict) else {}
    from auctelis.inventory.coverage import unparsed_agent_config_count_from_coverage

    unparsed = unparsed_agent_config_count_from_coverage(coverage)

    growth = label == "GROWTH"
    material = bool(summary.get("material_authority_change"))
    if baseline_state == "absent":
        # Absolute head reach, not a delta. Informational, exit 0.
        verdict = "BASELINE_NEEDED" if head_records else "PASS"
        label = "NONE"
        code = 0
    else:
        # ``tree`` (worktree extract) or ``present`` (committed-lock fallback).
        verdict = "NEEDS_REVIEW" if unparsed or growth or material else "PASS"
        code = 0 if verdict == "PASS" else 1

    findings_doc = {
        "findings": [],
        "coverage": coverage,
    }
    comment = render_authority_diff_comment(
        findings_doc,
        lock_delta=delta,
        verdict=verdict,
        baseline_state=baseline_state,
        trusted_hosts=trusted_hosts,
    )
    # Terminal stdout shows literal text; the payload keeps the escaped PR body.
    terminal_comment = render_authority_diff_comment(
        findings_doc,
        lock_delta=delta,
        verdict=verdict,
        baseline_state=baseline_state,
        trusted_hosts=trusted_hosts,
        plain_text=True,
    )
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "base_ref": base_ref,
        "baseline_state": baseline_state,
        "repository": str(repo),
        "verdict": verdict,
        "label": label,
        "delta": delta,
        "unparsed": unparsed,
        "comment": comment,
        "base_lock_hash": base.get("lock_hash"),
        "head_lock_hash": head.get("lock_hash"),
        "base_lock_drift": base_lock_drift,
    }
    lines = [
        f"auctelis diff --base {base_ref}",
        f"Verdict: {verdict} · label {label}",
        terminal_comment,
    ]
    if base_lock_drift:
        lines.append(
            "Note: committed base AUTHORITY.lock drifts from base tree-truth "
            "(diff used tree; reseal the lock on the base branch)."
        )
    return "\n".join(lines), result, code
