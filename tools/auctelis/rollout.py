"""Cross-platform lockless Watch PR opener (AUCT-044 / AUCT-045).

Reads a Reach Report and plans (or opens) one pull request per unwatched
repository that meets the tier filter. Dry-run is the default and performs no
HTTP. ``--apply`` uses stdlib ``urllib`` only, skips repos that already have an
Auctelis workflow or an open ``auctelis/watch-prs`` pull request, and resends
the workflow blob ``sha`` when GitHub requires it.

AUCT-045: PR bodies embed per-repo reach evidence + a literal ``Pin fix``;
``--repo`` / ``--min-tier`` target pilots; ``org_reusable`` defaults from the
report document when the CLI flag is omitted.
"""

from __future__ import annotations

import base64
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from auctelis.export.reach_report import (
    FLEET_REPORT_SCHEMA,
    REPORT_SCHEMA,
    lockless_workflow_yaml,
    org_reusable_caller_yaml,
)
from auctelis.github_audit import _api_base, _token, is_owner_repo_slug
from auctelis.textutil import escape_markdown_inline, markdown_code_span, validated_http_url

_BRANCH = "auctelis/watch-prs"
_WORKFLOW_PATH = ".github/workflows/auctelis.yml"
_WORKFLOW_DIR = ".github/workflows"
_WATCH_WORKFLOW_RE = re.compile(r"^auctelis.*\.ya?ml$", re.IGNORECASE)
_ORG_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_PR_TITLE = "Add auctelis lockless PR Watch"
_PR_BODY = (
    "Install Auctelis lockless PR Watch so future agent-authority changes "
    "surface in one quiet PR comment. No AUTHORITY.lock required."
)
_SCOPE_HINT = "gh auth refresh -s workflow"
_USER_AGENT = "auctelis-rollout"
_API_VERSION = "2022-11-28"
_MAX_BODY_LINES = 15
_MAX_FINDINGS = 3


def execute_rollout(
    report_path: Path,
    *,
    apply: bool,
    max_prs: int,
    org_reusable: str | None,
    as_json: bool,
    repos: list[str] | None = None,
    min_tier: int = 2,
) -> int:
    """Plan or open Watch PRs. Exit 0 when every target is opened or skipped."""
    if max_prs < 1:
        _say("auctelis rollout: --max-prs must be at least 1.", as_json=as_json, error=True)
        return 2
    if min_tier not in {1, 2}:
        _say("auctelis rollout: --min-tier must be 1 or 2.", as_json=as_json, error=True)
        return 2
    try:
        document = json.loads(report_path.read_text(encoding="utf-8"))
    except OSError as exc:
        _say(f"auctelis rollout: cannot read {report_path}: {exc}", as_json=as_json, error=True)
        return 2
    except json.JSONDecodeError as exc:
        _say(f"auctelis rollout: {report_path} is not JSON: {exc}", as_json=as_json, error=True)
        return 2
    if not isinstance(document, dict):
        _say("auctelis rollout: report JSON must be an object.", as_json=as_json, error=True)
        return 2
    schema = str(document.get("schema") or "")
    if schema and schema not in {REPORT_SCHEMA, FLEET_REPORT_SCHEMA}:
        _say(
            f"auctelis rollout: unsupported report schema {schema!r}.",
            as_json=as_json,
            error=True,
        )
        return 2

    # CLI --org-reusable wins; otherwise inherit from the Reach Report.
    org = str(org_reusable or "").strip().strip("/") or None
    if org is None:
        org = str(document.get("org_reusable") or "").strip().strip("/") or None

    if org is not None and not _ORG_RE.fullmatch(org):
        _say(
            "auctelis rollout: --org-reusable requires an org slug "
            "(letters, digits, dot, underscore, hyphen).",
            as_json=as_json,
            error=True,
        )
        return 2

    targets = select_targets(
        document,
        max_prs=max_prs,
        repos=repos,
        min_tier=min_tier,
    )
    mode = f"org-reusable:{org}" if org else "lockless"
    workflow = org_reusable_caller_yaml(org) if org else lockless_workflow_yaml()
    if not apply:
        results = [
            {
                "repository": str(repo.get("repository") or ""),
                "action": "would_open",
                "mode": mode,
            }
            for repo in targets
        ]
        _emit(results, apply=False, mode=mode, org_reusable=org, as_json=as_json, min_tier=min_tier)
        return 0

    token = _token()
    if not token:
        _say(
            "auctelis rollout: set GITHUB_TOKEN or GH_TOKEN, or run `gh auth login`.",
            as_json=as_json,
            error=True,
        )
        return 2
    results = [
        _apply_one(
            str(repo.get("repository") or ""),
            token=token,
            workflow=workflow,
            mode=mode,
            body=render_watch_pr_body(repo),
        )
        for repo in targets
    ]
    _emit(results, apply=True, mode=mode, org_reusable=org, as_json=as_json, min_tier=min_tier)
    if any(row.get("action") == "error" for row in results):
        return 1
    return 0


def select_targets(
    document: dict[str, Any],
    *,
    max_prs: int,
    repos: list[str] | None = None,
    min_tier: int = 2,
) -> list[dict[str, Any]]:
    """Unwatched repo documents meeting ``min_tier``, capped by ``max_prs``.

    ``repos`` (when set) is a case-insensitive ``owner/repo`` allow-list.
    """
    wanted: set[str] | None = None
    if repos:
        wanted = {str(slug).strip().lower() for slug in repos if str(slug).strip()}
        if not wanted:
            wanted = None
    matched: list[dict[str, Any]] = []
    for repo in _repo_documents(document):
        if repo.get("already_watching"):
            continue
        slug = str(repo.get("repository") or "").strip()
        if not is_owner_repo_slug(slug):
            continue
        if wanted is not None and slug.lower() not in wanted:
            continue
        reach_raw = repo.get("reach")
        reach = reach_raw if isinstance(reach_raw, dict) else {}
        tiers_raw = reach.get("tier_counts")
        tiers = tiers_raw if isinstance(tiers_raw, dict) else {}
        tier2 = int(tiers.get("tier2") or 0)
        tier1 = int(tiers.get("tier1") or 0)
        if min_tier >= 2:
            if tier2 <= 0:
                continue
        elif tier2 <= 0 and tier1 <= 0:
            continue
        matched.append(repo)
        if len(matched) >= max_prs:
            break
    return matched


def render_watch_pr_body(repo_doc: dict[str, Any]) -> str:
    """Compact evidence-backed Watch PR body (≤15 lines), or static fallback."""
    reach_raw = repo_doc.get("reach")
    reach = reach_raw if isinstance(reach_raw, dict) else {}
    ranked = [
        item for item in (reach.get("records") or reach.get("top") or []) if isinstance(item, dict)
    ]
    if not ranked:
        return _PR_BODY

    tiers_raw = reach.get("tier_counts")
    tiers = tiers_raw if isinstance(tiers_raw, dict) else {}
    slug = escape_markdown_inline(str(repo_doc.get("repository") or ""), max_len=120)
    lines: list[str] = [
        f"Install Auctelis lockless PR Watch on `{slug}` so future agent-authority "
        "changes surface in one quiet PR comment. No AUTHORITY.lock required.",
        "",
        (
            f"**Reach:** tier2={int(tiers.get('tier2') or 0)} · "
            f"tier1={int(tiers.get('tier1') or 0)} · "
            f"tier0={int(tiers.get('tier0') or 0)}"
        ),
        "",
        "**Top findings:**",
    ]
    pins_raw = repo_doc.get("pins")
    pins_doc = pins_raw if isinstance(pins_raw, dict) else {}
    pin_items = [item for item in (pins_doc.get("items") or []) if isinstance(item, dict)]
    pin_line = ""
    for item in ranked[:_MAX_FINDINGS]:
        name = escape_markdown_inline(str(item.get("name") or ""), max_len=80)
        path = escape_markdown_inline(str(item.get("path") or ""), max_len=80)
        reason = escape_markdown_inline(
            str(item.get("reason") or item.get("card") or ""), max_len=120
        )
        tier = int(item.get("tier") or 0)
        lines.append(f"- **{name}** (`{path}`) — tier {tier} · {reason}")
        if not pin_line:
            pin_line = _pin_fix_line(item, pin_items)

    if pin_line and len(lines) + 3 <= _MAX_BODY_LINES:
        lines.extend(["", pin_line])

    quiet = (
        "Quiet Watch: ordinary code/CI PRs stay silent; only agent-authority "
        "growth gets one sticky comment."
    )
    if len(lines) + 2 <= _MAX_BODY_LINES:
        lines.extend(["", quiet])

    while len(lines) > _MAX_BODY_LINES:
        # Drop the last finding bullet before the footer.
        if len(lines) > 6 and lines[5].startswith("- "):
            lines.pop(5)
        else:
            break
    return "\n".join(lines) + "\n"


def _pin_fix_line(item: dict[str, Any], pins: list[dict[str, Any]]) -> str:
    name = str(item.get("name") or "")
    path = str(item.get("path") or "")
    snippet = ""
    for pin in pins:
        if str(pin.get("name") or "") != name:
            continue
        pin_path = str(pin.get("path") or "")
        if path and pin_path and pin_path != path:
            continue
        snippet = str(pin.get("config_snippet") or "").strip()
        if snippet:
            break
    span = markdown_code_span(snippet) if snippet else None
    if not span:
        return ""
    return f"**Pin fix:** {span}"


def _repo_documents(document: dict[str, Any]) -> list[dict[str, Any]]:
    schema = str(document.get("schema") or "")
    repos = document.get("repositories")
    if schema == FLEET_REPORT_SCHEMA or isinstance(repos, list):
        return [repo for repo in repos if isinstance(repo, dict)] if isinstance(repos, list) else []
    if schema == REPORT_SCHEMA or document.get("repository"):
        return [document]
    return []


def _apply_one(
    slug: str,
    *,
    token: str,
    workflow: str,
    mode: str,
    body: str | None = None,
) -> dict[str, Any]:
    status, repo = _request("GET", _repo_api(slug), token=token)
    if status != 200 or not isinstance(repo, dict):
        return _error(slug, status, "repository lookup", mode)
    default_branch = str(repo.get("default_branch") or "main")

    present, watch_status = _watch_workflow_on_branch(slug, default_branch, token=token)
    if watch_status in {401, 403}:
        return _error(slug, watch_status, "workflow lookup", mode)
    if present:
        return {
            "repository": slug,
            "action": "skip_workflow",
            "mode": mode,
            "detail": "auctelis workflow already on the default branch",
        }

    owner = slug.split("/", 1)[0]
    pulls_path = (
        _repo_api(slug, "/pulls")
        + "?"
        + urllib.parse.urlencode({"state": "open", "head": f"{owner}:{_BRANCH}"})
    )
    status, pulls = _request("GET", pulls_path, token=token)
    if status in {401, 403}:
        return _error(slug, status, "pull request lookup", mode)
    if status == 200 and isinstance(pulls, list) and pulls:
        url = str((pulls[0] or {}).get("html_url") or "")
        return {
            "repository": slug,
            "action": "skip_open_pr",
            "mode": mode,
            "url": url,
            "detail": f"open Watch PR {url}".strip(),
        }

    ref_status, ref = _request(
        "GET",
        _repo_api(slug, f"/git/ref/heads/{urllib.parse.quote(default_branch, safe='/')}"),
        token=token,
    )
    sha = ""
    if ref_status == 200 and isinstance(ref, dict):
        sha = str((ref.get("object") or {}).get("sha") or "")
    if not sha:
        return _error(slug, ref_status, "default branch lookup", mode)

    branch_status, _branch = _request(
        "GET",
        _repo_api(slug, f"/git/ref/heads/{urllib.parse.quote(_BRANCH, safe='/')}"),
        token=token,
    )
    if branch_status == 404:
        created, _body = _request(
            "POST",
            _repo_api(slug, "/git/refs"),
            token=token,
            payload={"ref": f"refs/heads/{_BRANCH}", "sha": sha},
        )
        if created not in {200, 201}:
            return _error(slug, created, "create branch", mode)
    elif branch_status not in {200, 201}:
        return _error(slug, branch_status, "branch lookup", mode)

    put_status, _written = _put_workflow(slug, workflow, token=token)
    if put_status not in {200, 201}:
        return _error(slug, put_status, "write workflow", mode)

    pr_status, pr = _request(
        "POST",
        _repo_api(slug, "/pulls"),
        token=token,
        payload={
            "title": _PR_TITLE,
            "head": _BRANCH,
            "base": default_branch,
            "body": body or _PR_BODY,
        },
    )
    if pr_status in {200, 201} and isinstance(pr, dict):
        return {
            "repository": slug,
            "action": "opened",
            "mode": mode,
            "url": str(pr.get("html_url") or ""),
        }
    if pr_status == 422:
        status, existing = _request("GET", pulls_path, token=token)
        if status == 200 and isinstance(existing, list) and existing:
            url = str((existing[0] or {}).get("html_url") or "")
            return {
                "repository": slug,
                "action": "skip_open_pr",
                "mode": mode,
                "url": url,
                "detail": f"open Watch PR {url}".strip(),
            }
    return _error(slug, pr_status, "open pull request", mode)


def _watch_workflow_on_branch(slug: str, branch: str, *, token: str) -> tuple[bool, int]:
    path = _repo_api(slug, f"/contents/{_WORKFLOW_DIR}")
    path += "?" + urllib.parse.urlencode({"ref": branch})
    status, body = _request("GET", path, token=token)
    if status == 404:
        return False, status
    if status != 200 or not isinstance(body, list):
        return False, status
    for entry in body:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "")
        if _WATCH_WORKFLOW_RE.fullmatch(name):
            return True, status
    return False, status


def _put_workflow(slug: str, workflow: str, *, token: str) -> tuple[int, Any]:
    """Create or update the workflow file, retrying once with the blob sha."""
    blob_sha = _blob_sha(slug, token=token)
    status, body = _put_contents(slug, workflow, token=token, blob_sha=blob_sha)
    if status in {200, 201}:
        return status, body
    if status == 422 and not blob_sha:
        blob_sha = _blob_sha(slug, token=token)
        if blob_sha:
            return _put_contents(slug, workflow, token=token, blob_sha=blob_sha)
    return status, body


def _blob_sha(slug: str, *, token: str) -> str:
    path = _repo_api(slug, f"/contents/{_WORKFLOW_PATH}")
    path += "?" + urllib.parse.urlencode({"ref": _BRANCH})
    status, body = _request("GET", path, token=token)
    if status == 200 and isinstance(body, dict):
        return str(body.get("sha") or "")
    return ""


def _put_contents(
    slug: str,
    workflow: str,
    *,
    token: str,
    blob_sha: str,
) -> tuple[int, Any]:
    payload: dict[str, Any] = {
        "message": "Add auctelis lockless PR Watch workflow",
        "content": base64.b64encode(workflow.encode("utf-8")).decode("ascii"),
        "branch": _BRANCH,
    }
    if blob_sha:
        payload["sha"] = blob_sha
    return _request(
        "PUT", _repo_api(slug, f"/contents/{_WORKFLOW_PATH}"), token=token, payload=payload
    )


def _repo_api(slug: str, suffix: str = "") -> str:
    owner, repo = slug.split("/", 1)
    path = f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
    if not suffix:
        return path
    if not suffix.startswith("/"):
        suffix = "/" + suffix
    return path + suffix


def _request(
    method: str,
    path: str,
    *,
    token: str | None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    url = validated_http_url(_api_base().rstrip("/") + path, what="GitHub API URL")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": _USER_AGENT,
        "X-GitHub-Api-Version": _API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            raw = resp.read()
            status = int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        status = int(exc.code)
    except urllib.error.URLError as exc:
        return 0, {"message": str(exc.reason)}
    if not raw:
        return status, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return status, {"message": raw.decode("utf-8", errors="replace")}


def _error(slug: str, status: int, what: str, mode: str) -> dict[str, Any]:
    detail = f"{what} failed (HTTP {status})"
    hint = ""
    if status in {403, 422}:
        hint = _SCOPE_HINT
        detail = f"{detail} — if the token is missing the workflow scope, run: {hint}"
    return {
        "repository": slug,
        "action": "error",
        "mode": mode,
        "status": status,
        "detail": detail,
        "scope_hint": hint,
    }


def _emit(
    results: list[dict[str, Any]],
    *,
    apply: bool,
    mode: str,
    org_reusable: str | None,
    as_json: bool,
    min_tier: int = 2,
) -> None:
    payload = {
        "apply": apply,
        "mode": mode,
        "org_reusable": org_reusable,
        "min_tier": min_tier,
        "planned": [row["repository"] for row in results],
        "results": results,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    label = "apply" if apply else "dry-run"
    print(f"auctelis rollout · {label} · {len(results)} repo(s) · mode={mode}")
    if not results:
        tier_label = "tier-2" if min_tier >= 2 else "tier-1+"
        print(f"No unwatched {tier_label} repositories to roll out.")
        return
    for row in results:
        repo = row.get("repository")
        action = row.get("action")
        if action == "would_open":
            print(f"  {repo} · would open Watch PR on {_BRANCH}")
        elif action == "opened":
            print(f"  {repo} · opened {row.get('url') or _BRANCH}")
        elif action == "skip_workflow":
            print(f"  {repo} · skip — auctelis workflow already on the default branch")
        elif action == "skip_open_pr":
            print(f"  {repo} · skip — {row.get('detail') or 'open Watch PR'}")
        else:
            print(f"  {repo} · {row.get('detail') or action}")
    if not apply:
        print("Dry-run only. Re-run with --apply to open Watch PRs.")


def _say(message: str, *, as_json: bool, error: bool) -> None:
    stream = sys.stderr if error or as_json else sys.stdout
    print(message, file=stream)
