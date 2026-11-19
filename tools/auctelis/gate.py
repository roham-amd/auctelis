"""Authority gate: tree-truth base→head diff + CODEOWNERS + ruleset check.

Product contract: GitHub CODEOWNERS / rulesets enforce human review. auctelis
owns the authority diff:

1. Derive head authority from the working tree (never trust a committed lock
   as head). Compare an optional committed lock for drift only.
2. Schema-validate the base lock; empty (0-record) bases are empty-baseline growth.
3. On growth, require CODEOWNERS coverage for the lock and for grown authority
   paths; label growth vs reduction. Do **not** count PR reviews — that is
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

from auctelis.authority_card import reach_snapshot
from auctelis.authority_lock import (
    LOCK_NAME,
    build_authority_lock,
    delta_label,
    diff_authority_locks,
)
from auctelis.lock_io import AuthorityLockError, load_authority_lock
from auctelis.reach_tiers import (
    TIER_COMMENT,
    TIER_FAIL,
    delta_max_reach_tier,
    load_trusted_hosts,
)
from auctelis.security.engine import ScanResult, run_authority_inventory
from auctelis.textutil import validated_http_url

TRUST_FILE = ".auctelis/trusted-hosts"

# Authority-bearing path globs that CODEOWNERS should cover (docs + code).
AUTHORITY_PATH_HINTS = (
    LOCK_NAME,
    ".auctelis.yml",
    TRUST_FILE,
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


# Concrete paths probed for gate self-protection (CODEOWNERS last-match).
_PROTECTION_TARGETS = (
    LOCK_NAME,
    ".auctelis.yml",
    ".github/workflows/auctelis-gate.yml",
    ".github/actions/auctelis-gate/action.yml",
    "CODEOWNERS",
    ".github/CODEOWNERS",
)


def _codeowners_owners_for(codeowners_text: str, target: str) -> list[str]:
    """Owners for ``target``, honoring directory / glob CODEOWNERS rules."""
    direct = parse_codeowners_for_path(codeowners_text, target=target)
    if direct:
        return direct
    # Directory rules: `.github/workflows/` covers nested workflow files.
    owners: list[str] = []
    target_norm = target.replace("\\", "/").lstrip("/")
    for raw in codeowners_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        pattern, *rest = parts
        normalized = pattern.replace("\\", "/").lstrip("/")
        matched = False
        if (
            normalized in {"*", "**"}
            or (normalized.endswith("/") and target_norm.startswith(normalized))
            or (normalized.endswith("/**") and target_norm.startswith(normalized[:-2]))
            or (normalized.endswith("/**/*") and target_norm.startswith(normalized[:-4]))
            or (normalized.rstrip("/") and target_norm.startswith(normalized.rstrip("/") + "/"))
        ):
            matched = True
        if matched:
            owners = [t for t in rest if t.startswith("@")]
    return owners


def codeowners_covers_path(codeowners_text: str, target: str) -> bool:
    return bool(_codeowners_owners_for(codeowners_text, target))


def codeowners_covers_protection(
    codeowners_text: str,
    *,
    root: Path | None = None,
) -> tuple[bool, list[str]]:
    """Return ``(ok, missing_paths)`` for lock + existing gate self-protection paths.

    When ``root`` is set, only paths that exist on disk are required (plus
    ``AUTHORITY.lock``). Init templates still emit the full set.
    """
    if not codeowners_text.strip():
        return False, [LOCK_NAME]

    targets: list[str]
    if root is None:
        targets = list(_PROTECTION_TARGETS)
    else:
        targets = [LOCK_NAME]
        # Only repos that actually use trusted hosts must cover the file.
        if (root / TRUST_FILE).is_file():
            targets.append(TRUST_FILE)
        gate_installed = (root / ".github" / "workflows" / "auctelis-gate.yml").is_file() or (
            root / ".github" / "actions" / "auctelis-gate" / "action.yml"
        ).is_file()
        for rel in _PROTECTION_TARGETS:
            if rel == LOCK_NAME:
                continue
            if rel in {"CODEOWNERS", ".github/CODEOWNERS"}:
                # Self-cover CODEOWNERS once the gate workflow/action is installed.
                if gate_installed and any(
                    (root / cand).is_file() for cand in (".github/CODEOWNERS", "CODEOWNERS")
                ):
                    targets.append(rel)
                continue
            if (root / rel).is_file() or (root / rel).is_dir():
                targets.append(rel)
        # Deduplicate while preserving order.
        seen: set[str] = set()
        deduped: list[str] = []
        for t in targets:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        targets = deduped

    missing = [target for target in targets if not codeowners_covers_path(codeowners_text, target)]
    # CODEOWNERS / .github/CODEOWNERS: covering either form is enough.
    co_missing = [p for p in missing if p in {"CODEOWNERS", ".github/CODEOWNERS"}]
    if len(co_missing) == 1:
        missing = [p for p in missing if p not in {"CODEOWNERS", ".github/CODEOWNERS"}]
    elif len(co_missing) >= 2:
        missing = [p for p in missing if p not in {"CODEOWNERS", ".github/CODEOWNERS"}]
        missing.append(".github/CODEOWNERS")
    return (not missing), missing


def _api_get_json(url: str, *, token: str) -> tuple[Any | None, int]:
    try:
        url = validated_http_url(url, what="GitHub API URL")
    except ValueError:
        return None, 0
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
        # Scheme/host validated above; only http(s) reaches urlopen.
        with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
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

    Prefers GitHub's effective rules endpoint
    (``/repos/{repo}/rules/branches/{branch}``) so disabled or non-applicable
    rulesets are not treated as ``OK``. Falls back to ruleset list + classic
    branch protection.
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
    if not branch:
        meta, mstatus = _api_get_json(f"{base}/repos/{repo}", token=tok)
        if mstatus == 200 and isinstance(meta, dict):
            branch = str(meta.get("default_branch") or "") or None

    # Effective rules for the branch (preferred — respects enforcement=active).
    if branch:
        effective, estatus = _api_get_json(
            f"{base}/repos/{repo}/rules/branches/{branch}", token=tok
        )
        if estatus in {401, 403}:
            return "UNVERIFIED", f"effective-rules API returned HTTP {estatus} (token scope?)"
        if estatus == 200 and isinstance(effective, list):
            for rule in effective:
                if not isinstance(rule, dict):
                    continue
                if str(rule.get("type") or "") != "pull_request":
                    continue
                params = rule.get("parameters") or {}
                if isinstance(params, dict) and params.get("require_code_owner_review"):
                    return (
                        "OK",
                        f"effective rules on {branch} require code-owner review",
                    )
            # Effective rules listed but none require code owners — try classic.

    # Rulesets list (legacy path / when effective rules unavailable).
    payload, status = _api_get_json(f"{base}/repos/{repo}/rulesets", token=tok)
    if status in {401, 403}:
        return "UNVERIFIED", f"rulesets API returned HTTP {status} (token scope?)"
    if status == 200 and isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            # Disabled rulesets are not protection.
            if str(item.get("enforcement") or "").lower() == "disabled":
                continue
            rules = item.get("rules") or []
            detail_doc = item
            if not isinstance(rules, list) or not rules:
                rid = item.get("id")
                if rid is None:
                    continue
                detail, dstatus = _api_get_json(f"{base}/repos/{repo}/rulesets/{rid}", token=tok)
                if dstatus != 200 or not isinstance(detail, dict):
                    continue
                detail_doc = detail
                if str(detail_doc.get("enforcement") or "").lower() == "disabled":
                    continue
                rules = detail_doc.get("rules") or []
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

    # Classic branch protection fallback.
    # Note: github.token has no Administration scope — classic protection often
    # returns 403 and surfaces as UNVERIFIED under strict mode.
    if branch:
        prot, pstatus = _api_get_json(
            f"{base}/repos/{repo}/branches/{branch}/protection", token=tok
        )
        if pstatus in {401, 403}:
            return (
                "UNVERIFIED",
                f"branch protection API returned HTTP {pstatus} "
                "(classic protection needs Administration scope; prefer a ruleset)",
            )
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
    codeowners_covers: bool | None = None,
    base_ref_resolved: bool = True,
    missing_protection_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Distinguish first-lock adoption from a normal growth-gate pass.

    Used by the GitHub Action (and tests) when there is no base-ref lock.
    ``BASELINE_ADOPTED`` is **not** equivalent to ``PASS`` on a growth gate.
    Adoption requires a resolved base ref and CODEOWNERS protection coverage.
    """
    if not base_ref_resolved:
        return {
            "ok": False,
            "ceremony": "fail_closed",
            "verdict": "FAIL_CLOSED",
            "message": (
                "Base ref could not be resolved — fail closed. "
                "BASELINE_ADOPTED only applies when the base ref resolves and "
                "has no AUTHORITY.lock."
            ),
        }
    if base_lock_present:
        return {
            "ok": True,
            "ceremony": "growth_gate",
            "verdict": "PASS",
            "message": "Base lock present — run auctelis gate for authority growth.",
        }
    if head_lock_present:
        if codeowners_covers is False:
            missing = ", ".join(missing_protection_paths or []) or "AUTHORITY.lock"
            return {
                "ok": False,
                "ceremony": "fail_closed",
                "verdict": "NEEDS_REVIEW",
                "message": (
                    "First AUTHORITY.lock on head, but CODEOWNERS does not cover "
                    f"protection paths ({missing}). Add owners before treating "
                    "this as BASELINE_ADOPTED."
                ),
            }
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


def committed_lock_drift(
    root: Path,
    tree_head: dict[str, Any],
    *,
    head_lock: Path | None = None,
    require_committed: bool = False,
    base_had_records: bool = False,
) -> tuple[bool, list[str], str | None]:
    """Compare a committed AUTHORITY.lock to tree-derived head authority.

    Returns ``(drifted, lines, error)``. ``--head-lock`` is comparison-only —
    never the gate's head authority source.

    When ``require_committed`` is true (enforce) and the base lock sealed
    records, deleting the head lock is drift — not a silent lockless PASS.
    """
    path = head_lock
    if path is None:
        candidate = root / LOCK_NAME
        path = candidate if candidate.is_file() else None
    if path is None:
        if require_committed and base_had_records:
            return (
                True,
                [],
                "AUTHORITY.lock absent on head while base lock has sealed records "
                "(deleting the lock is not a bypass — switch locked=false first, "
                "then remove the lock)",
            )
        return False, [], None
    if not path.is_file():
        if require_committed and base_had_records:
            return (
                True,
                [],
                f"AUTHORITY.lock absent on head ({path}) while base lock has sealed records",
            )
        return True, [], f"head lock not found: {path}"
    try:
        committed = load_authority_lock(path)
    except (AuthorityLockError, FileNotFoundError, OSError) as exc:
        return True, [], f"cannot read committed head lock {path}: {exc}"
    delta = diff_authority_locks(committed, tree_head)
    summary = delta.get("summary") or {}
    if not bool(summary.get("authority_changed")):
        return False, [], None
    lines = [str(line) for line in (delta.get("lines") or [])]
    return True, lines, None


def uncovered_authority_paths(
    head: dict[str, Any],
    codeowners_text: str,
    *,
    delta: dict[str, Any] | None = None,
) -> list[str]:
    """Authority paths that grew on head and are not CODEOWNERS-covered.

    When ``delta`` is provided, only added/changed record paths are required —
    stable baseline paths already sealed under lock-only CODEOWNERS are not
    retroactively failing every green gate.
    """
    if not codeowners_text.strip():
        return []
    paths: list[str] = []
    seen: set[str] = set()

    def _add(rec: dict[str, Any] | None) -> None:
        if not isinstance(rec, dict):
            return
        path = str(rec.get("path") or "").replace("\\", "/")
        if path.startswith("./"):
            path = path[2:]
        if not path or path in seen:
            return
        seen.add(path)
        paths.append(path)

    if delta:
        changes = delta.get("changes") or {}
        for rec in changes.get("added") or []:
            _add(rec if isinstance(rec, dict) else None)
        for item in changes.get("changed") or []:
            if isinstance(item, dict):
                _add(item.get("after") if isinstance(item.get("after"), dict) else item)
    else:
        for rec in head.get("records") or []:
            _add(rec if isinstance(rec, dict) else None)

    return [p for p in paths if not codeowners_covers_path(codeowners_text, p)]


def _fail_closed_gate_report(error: str) -> tuple[dict[str, Any], int]:
    return {
        "ok": False,
        "verdict": "FAIL_CLOSED",
        "error": error,
        "needs_approval": True,
        "required_owners": [],
        "label": "GROWTH",
        "ruleset": "UNVERIFIED",
        "lines": [],
    }, 2


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
    trust_head_codeowners: bool = False,
    codeowners_from_base: bool = False,
    comment_only: bool = False,
) -> tuple[dict[str, Any], int]:
    """Compare base→head tree authority; fail on growth without CODEOWNERS.

    Head authority is **always** derived from the working tree. A committed
    ``AUTHORITY.lock`` (or ``--head-lock``) is compared for drift only — never
    trusted as the head snapshot.

    ``strict_ruleset`` defaults to True: UNVERIFIED protection on growth is
    NEEDS_REVIEW, not a green PASS. Pass False for best-effort.

    When CODEOWNERS is loaded from the head tree (not a trusted base-ref copy),
    growth requires ``trust_head_codeowners=True`` — otherwise NEEDS_REVIEW.

    ``comment_only`` (lockless / ``locked=false`` Action): still posts the
    Authority Diff, but growth / CODEOWNERS / ruleset gaps do not fail the
    required check. Unparsed configs and lock↔tree drift stay visible.
    """
    root = root.resolve()
    if base_lock.is_dir():
        return _fail_closed_gate_report(
            f"--base-lock expects an AUTHORITY.lock file, not a directory "
            f"({base_lock}). Pass the lock path (e.g. /tmp/base.lock)."
        )
    try:
        base = load_authority_lock(base_lock)
    except (AuthorityLockError, FileNotFoundError, OSError) as exc:
        return _fail_closed_gate_report(f"cannot read base lock {base_lock}: {exc}")
    # Explicit --head-lock that is missing still fails closed (caller promised a file).
    if head_lock is not None and not head_lock.is_file():
        return _fail_closed_gate_report(f"head lock not found: {head_lock}")
    try:
        if scan is None:
            scan = run_authority_inventory(root)
        head = build_authority_lock(root, scan=scan)
    except (AuthorityLockError, FileNotFoundError, OSError, ValueError) as exc:
        return _fail_closed_gate_report(str(exc))
    coverage = scan.coverage if isinstance(scan.coverage, dict) else {}
    try:
        unparsed = int(coverage.get("unparsed_agent_config_count") or 0)
    except (TypeError, ValueError):
        unparsed = 0
    from auctelis.inventory.coverage import count_truncation_events

    trunc = count_truncation_events(coverage.get("parser_events"))
    coverage = {
        **coverage,
        "depth_limit_count": trunc["depth_limit"],
        "file_limit_reached_count": trunc["file_limit_reached"],
        "read_error_count": trunc["read_error"],
        "truncated": bool(trunc["depth_limit"] or trunc["file_limit_reached"]),
    }

    base_records = list(base.get("records") or [])
    head_records = list(head.get("records") or [])
    lock_drift, drift_lines, drift_error = committed_lock_drift(
        root,
        head,
        head_lock=head_lock,
        require_committed=not comment_only,
        base_had_records=bool(base_records) or bool(base.get("mcp_tools") or {}),
    )
    # Empty (0-record) base locks are a valid seal of a clean tree. First real
    # authority is GROWTH that needs CODEOWNERS — never a permanent FAIL_CLOSED.
    empty_baseline_growth = (
        not base_records and not (base.get("mcp_tools") or {}) and bool(head_records)
    )

    owners = load_lock_owners(
        root, codeowners_path=codeowners_path, codeowners_text=codeowners_text
    )
    co_text = (
        codeowners_text
        if codeowners_text is not None
        else load_codeowners_text(root, codeowners_path=codeowners_path)
    )
    # Trusted hosts are as attacker-writable as head CODEOWNERS on a PR. Honor
    # them only when the trust file itself is CODEOWNERS-covered; otherwise a PR
    # could allowlist its own destination and lower its own reach tier. Deleting
    # the file only makes the gate stricter, so absence is not a bypass.
    trusted_hosts = load_trusted_hosts(root)
    trusted_hosts_ignored = False
    if trusted_hosts and not (co_text and codeowners_covers_path(co_text, TRUST_FILE)):
        trusted_hosts = set()
        trusted_hosts_ignored = True
    delta = diff_authority_locks(base, head, trusted_hosts=trusted_hosts)
    summary = delta.get("summary") or {}
    meaningful = bool(summary.get("meaningful_authority_change"))
    # Align with check / lock --check: representation / body drift is reviewable.
    authority_changed = bool(summary.get("authority_changed"))
    label = growth_label(summary if isinstance(summary, dict) else {})
    owners_present = codeowners_covers_lock(co_text) if co_text else bool(owners)
    protection_ok, missing_protection = (
        codeowners_covers_protection(co_text, root=root) if co_text else (False, [LOCK_NAME])
    )
    uncovered_paths = uncovered_authority_paths(head, co_text, delta=delta) if co_text else []
    max_tier = int(
        summary.get("max_reach_tier") or delta_max_reach_tier(delta, trusted_hosts=trusted_hosts)
    )
    # Tier 0/1 growth stays on the comment; only tier ≥ fail (execute/secrets/MCP…)
    # pages CODEOWNERS / fails the required check.
    needs_approval = label == "GROWTH" and max_tier >= TIER_FAIL
    trust_warning = (
        "`.auctelis/trusted-hosts` is not covered by CODEOWNERS — trusted "
        "destinations were ignored for this run. Add a CODEOWNERS entry for it."
        if trusted_hosts_ignored
        else None
    )
    # Head CODEOWNERS alone is attacker-writable on a PR. Trust it only when:
    # - caller passed a base-ref copy (--codeowners / codeowners_text), or
    # - --trust-head-codeowners, or
    # - ruleset probe is skipped (local --skip-ruleset-check).
    trusted_codeowners = bool(
        codeowners_from_base
        or trust_head_codeowners
        or codeowners_path is not None
        or codeowners_text is not None
        or not check_ruleset
    )
    head_codeowners_untrusted = needs_approval and owners_present and not trusted_codeowners
    ruleset_status, ruleset_detail = "UNVERIFIED", "not checked"
    if check_ruleset and needs_approval:
        ruleset_status, ruleset_detail = check_code_owner_ruleset(
            repository=repository, token=token
        )

    ok = True
    verdict = "PASS"
    error: str | None = None
    if needs_approval and head_codeowners_untrusted:
        ok = False
        verdict = "NEEDS_REVIEW"
        error = (
            "CODEOWNERS was read from the head tree (not a trusted base ref). "
            "Pass --codeowners <base-ref-copy> or --trust-head-codeowners "
            "(unsafe) to accept head CODEOWNERS for this growth gate."
        )
    elif needs_approval and not owners_present:
        ok = False
        verdict = "NEEDS_REVIEW"
        error = (
            "AUTHORITY.lock has no CODEOWNERS entry on the trusted ref; "
            "cannot rely on GitHub-native review. "
            "Run `auctelis init --owner security` and protect authority paths."
        )
    elif needs_approval and not protection_ok:
        ok = False
        verdict = "NEEDS_REVIEW"
        missing = ", ".join(missing_protection) or "protection paths"
        error = (
            f"CODEOWNERS is missing coverage for gate self-protection ({missing}). "
            "Cover AUTHORITY.lock, .auctelis.yml, .github/workflows/, "
            ".github/actions/, and CODEOWNERS."
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

    def _append_review_error(detail: str) -> None:
        """Append a NEEDS_REVIEW detail; drop stale PASS labels from earlier branches."""
        nonlocal error
        prior = error
        if prior and prior.lstrip().startswith("PASS"):
            prior = None
        error = f"{prior} {detail}".strip() if prior else detail

    # Unparsed configs mean authority could not be established. Never let a
    # missing record look like a reduction/PASS.
    if unparsed:
        ok = False
        verdict = "NEEDS_REVIEW"
        detail = (
            f"{unparsed} agent config file(s) could not be parsed on head — review before merge."
        )
        _append_review_error(detail)

    # Walk truncation under enforce is the same class of incomplete authority as
    # unparsed configs — never green-light a scan that hit file/depth caps.
    truncated = bool(coverage.get("truncated"))
    if truncated and not comment_only:
        ok = False
        verdict = "NEEDS_REVIEW"
        detail = (
            "inventory truncated (file or depth limit reached) — "
            "review incomplete coverage before merge, or raise scan limits."
        )
        _append_review_error(detail)

    # Committed lock must match the tree; otherwise the gate would green-light
    # authority that never entered the lock (the classic bypass).
    if lock_drift or drift_error:
        ok = False
        verdict = "NEEDS_REVIEW"
        if drift_error:
            detail = f"{drift_error} — run `auctelis lock` and review."
        else:
            shown = "; ".join(drift_lines[:8]) if drift_lines else "authority fields differ"
            detail = f"committed AUTHORITY.lock ≠ tree ({shown}) — run `auctelis lock` and review."
        _append_review_error(detail)

    # Representation / body-only churn is visible on the PR comment but is not
    # material reach. Local `check` / `lock --check` still refuse an unsealed
    # body digest; the required CI check fails only on material growth, drift,
    # unparsed configs, or missing CODEOWNERS/ruleset protection.
    material = (
        bool(summary.get("material_authority_change")) if isinstance(summary, dict) else meaningful
    )
    representation_only = bool(authority_changed and not material and label == "NONE")
    if ok and representation_only:
        note = "authority body/representation changed on head (visible on comment; not material reach)."
        error = f"{error} {note}".strip() if error else note

    # Every discovered authority path should be CODEOWNERS-covered on material
    # growth or lock↔tree drift (not on body-only packaging churn).
    if uncovered_paths and (needs_approval or material or lock_drift):
        ok = False
        verdict = "NEEDS_REVIEW"
        shown = ", ".join(uncovered_paths[:8])
        more = f" (+{len(uncovered_paths) - 8} more)" if len(uncovered_paths) > 8 else ""
        detail = f"CODEOWNERS missing coverage for authority paths: {shown}{more}."
        _append_review_error(detail)

    if empty_baseline_growth:
        note = (
            "Empty-baseline growth: base AUTHORITY.lock has 0 records; "
            "first sealed authority requires CODEOWNERS review (not FAIL_CLOSED)."
        )
        if error and error.lstrip().startswith("PASS"):
            error = None
        error = f"{error} {note}".strip() if error else note

    mode = "comment-only" if comment_only else "enforce"
    if comment_only:
        # The required check stays green (advisory), but the verdict must stay
        # honest: unreviewed network-or-worse growth is NEEDS_REVIEW, never PASS.
        # Only NONE / REDUCTION / tier-0 growth can say PASS.
        ok = True
        if unparsed or lock_drift or truncated:
            note = "comment-only — advisory; required check does not fail, review still required."
        elif label == "GROWTH" and max_tier >= TIER_COMMENT:
            verdict = "NEEDS_REVIEW"
            note = (
                "comment-only — unreviewed growth is advisory; "
                "CODEOWNERS review required before merge."
            )
        else:
            verdict = "PASS"
            note = "comment-only — no unreviewed reach; required check stays green."
        if error and error.lstrip().startswith("PASS"):
            error = note
        else:
            error = f"{error} {note}".strip() if error else note

    if trust_warning and (not error or trust_warning not in error):
        error = f"{error} {trust_warning}".strip() if error else trust_warning

    protection = protection_status(ruleset_status, needs_approval=needs_approval)
    report_lines = list(delta.get("lines") or [])
    if drift_lines:
        report_lines = [*report_lines, *[f"! lock↔tree {line}" for line in drift_lines]]
    report: dict[str, Any] = {
        "ok": ok,
        "verdict": verdict,
        "mode": mode,
        "ceremony": "empty_baseline_growth" if empty_baseline_growth else "growth_gate",
        "protection": protection,
        "strict_ruleset": strict_ruleset,
        "meaningful_authority_change": meaningful,
        "material_authority_change": material,
        "representation_only": representation_only,
        "authority_changed": authority_changed,
        "lock_tree_drift": lock_drift,
        "needs_approval": needs_approval,
        "empty_baseline_growth": empty_baseline_growth,
        "label": label,
        "max_reach_tier": max_tier,
        "trusted_hosts_ignored": trusted_hosts_ignored,
        "required_owners": owners,
        "owners_present": owners_present,
        "protection_paths_covered": protection_ok,
        "missing_protection_paths": missing_protection,
        "uncovered_authority_paths": uncovered_paths,
        "ruleset": ruleset_status,
        "ruleset_detail": ruleset_detail,
        "delta": delta,
        "coverage": coverage,
        "unparsed": unparsed,
        "lines": report_lines,
        "authority_path_hints": list(AUTHORITY_PATH_HINTS),
        "head_source": "tree",
        # Reach snapshot of head authority: lets the Action prove a fresh
        # install is watching something even on a no-change ("quiet") PR.
        "reach": reach_snapshot(head_records, limit=5, trusted_hosts=trusted_hosts),
    }
    if error:
        report["error"] = error
    return report, 0 if ok else 1


def render_gate_report(report: dict[str, Any]) -> str:
    verdict = str(report.get("verdict") or "UNKNOWN")
    protection = str(report.get("protection") or "")
    mode = str(report.get("mode") or "")
    if verdict == "PASS" and protection == "verified":
        header = "auctelis gate — PASS / protection verified"
    elif verdict == "PASS" and protection == "unverified":
        header = "auctelis gate — PASS / protection unverified"
    elif verdict == "BASELINE_ADOPTED":
        header = "auctelis gate — BASELINE_ADOPTED (adoption ceremony, not growth PASS)"
    else:
        header = f"auctelis gate — {verdict}"
    if mode == "comment-only":
        if verdict == "NEEDS_REVIEW":
            header = (
                "auctelis gate — NEEDS_REVIEW · mode comment-only (advisory; check not failing)"
            )
        else:
            header = f"{header} · mode comment-only"
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
        ruleset_detail = str(report.get("ruleset_detail") or "")
        if (
            ruleset_detail == "not checked"
            or "ruleset check skipped" in str(report.get("error") or "").lower()
        ):
            lines.append("Ruleset check skipped")
        elif report.get("strict_ruleset"):
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
    elif report.get("ok") and report.get("representation_only"):
        lines.append(
            "Body/representation changed vs base lock — visible on comment; "
            "not material reach (required check stays green)."
        )
    elif report.get("ok") and not report.get("needs_approval") and label == "NONE":
        lines.append("No material authority growth vs base lock.")
    if mode == "comment-only" and label == "GROWTH":
        lines.append(
            "Advisory: review the growth above; the required check does not fail "
            "until enforce is armed."
        )
    return "\n".join(lines)
