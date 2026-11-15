"""Local PR Authority Diff simulator — ``auctelis diff --base <ref>``.

Reads the base ``AUTHORITY.lock`` via ``git show``, regenerates the head lock
from the working tree, and renders the same comment dialect as the Action.
"""

from __future__ import annotations

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
from auctelis.check import SCHEMA_VERSION
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.lock_io import AuthorityLockError, load_authority_lock
from auctelis.security.engine import run_security_scan


def _git_show(repo: Path, ref: str, relpath: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{relpath}"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


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
    raw = _git_show(repo, base_ref, lock_name)
    if raw is None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "verdict": "FAIL_CLOSED",
            "error": (
                f"cannot read {lock_name} from git ref {base_ref!r} "
                f"(git show {base_ref}:{lock_name})"
            ),
            "base_ref": base_ref,
        }
        return (
            f"auctelis diff --base: {payload['error']}",
            payload,
            2,
        )

    with tempfile.TemporaryDirectory(prefix="auctelis-diff-base-") as tmp:
        base_path = Path(tmp) / lock_name
        base_path.write_text(raw, encoding="utf-8")
        try:
            base = load_authority_lock(base_path)
        except (AuthorityLockError, OSError) as exc:
            payload = {
                "schema_version": SCHEMA_VERSION,
                "verdict": "FAIL_CLOSED",
                "error": f"base lock from {base_ref!r} is unusable: {exc}",
                "base_ref": base_ref,
            }
            return f"auctelis diff --base: {payload['error']}", payload, 2

    scan = run_security_scan(repo)
    head = build_authority_lock(repo, scan=scan)
    delta = diff_authority_locks(base, head)
    summary = dict(delta.get("summary") or {})
    label = delta_label(summary)
    coverage = scan.coverage if isinstance(scan.coverage, dict) else {}
    try:
        unparsed = int(coverage.get("unparsed_agent_config_count") or 0)
    except (TypeError, ValueError):
        unparsed = 0

    growth = label == "GROWTH"
    if unparsed or growth or summary.get("meaningful_authority_change"):
        verdict = "NEEDS_REVIEW"
    else:
        verdict = "PASS"

    findings_doc = {
        "findings": [],
        "coverage": coverage,
    }
    comment = render_authority_diff_comment(
        findings_doc,
        lock_delta=delta,
        verdict=verdict,
    )
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "base_ref": base_ref,
        "repository": str(repo),
        "verdict": verdict,
        "label": label,
        "delta": delta,
        "unparsed": unparsed,
        "comment": comment,
        "base_lock_hash": base.get("lock_hash"),
        "head_lock_hash": head.get("lock_hash"),
    }
    lines = [
        f"auctelis diff --base {base_ref}",
        f"Verdict: {verdict} · label {label}",
        comment,
    ]
    code = 0 if verdict == "PASS" else 1
    return "\n".join(lines), result, code
