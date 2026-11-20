"""Zero-clone GitHub org/repo Reach Audit via Trees + Blobs API (AUCT-022).

Uses stdlib ``urllib`` only. Fetches watched agent-config paths into a temp
directory, runs the normal check inventory, and never clones a git repo.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from auctelis.inventory.watched_paths import (
    DEFAULT_MAX_FILE_BYTES,
    MAX_WATCHED_FILES_PER_REPO,
    is_watched_path,
)
from auctelis.textutil import validated_http_url

_USER_AGENT = "auctelis-github-audit"
_API_VERSION = "2022-11-28"


class GitHubAuditError(Exception):
    """Honest fail for auth, rate-limit, or unreachable GitHub API."""

    def __init__(self, message: str, *, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class RepoAuditResult:
    """One repository audit outcome (success or skipped/truncated)."""

    repository: str
    report: dict[str, Any] | None = None
    scan: Any = None
    cards: list[str] | None = None
    notes: list[str] = field(default_factory=list)
    skipped: bool = False
    truncated: bool = False


def _api_base() -> str:
    return (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")


def _token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    return tok.strip() if tok and tok.strip() else None


def _request_json(
    url: str,
    *,
    token: str | None,
    accept: str = "application/vnd.github+json",
) -> tuple[Any | None, int, dict[str, str]]:
    try:
        url = validated_http_url(url, what="GitHub API URL")
    except ValueError as exc:
        raise GitHubAuditError(f"invalid GitHub API URL: {exc}") from exc
    headers = {
        "Accept": accept,
        "User-Agent": _USER_AGENT,
        "X-GitHub-Api-Version": _API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            body = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            if not body:
                return None, int(resp.status), hdrs
            return json.loads(body.decode("utf-8")), int(resp.status), hdrs
    except urllib.error.HTTPError as exc:
        hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        if exc.code in {401, 403, 429}:
            detail = "rate limit or auth" if exc.code in {403, 429} else "unauthorized"
            raise GitHubAuditError(
                f"GitHub API HTTP {exc.code} ({detail}) for {url}",
                status=exc.code,
            ) from exc
        return None, int(exc.code), hdrs
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, TypeError) as exc:
        raise GitHubAuditError(f"GitHub API request failed: {exc}") from exc


def _paginate(
    url: str,
    *,
    token: str | None,
    max_items: int,
) -> list[dict[str, Any]]:
    """Follow Link: rel=next until ``max_items`` collected."""
    out: list[dict[str, Any]] = []
    next_url: str | None = url
    while next_url and len(out) < max_items:
        data, status, hdrs = _request_json(next_url, token=token)
        if status == 404:
            break
        if status != 200 or not isinstance(data, list):
            raise GitHubAuditError(f"unexpected list response HTTP {status} for {next_url}")
        for item in data:
            if isinstance(item, dict):
                out.append(item)
                if len(out) >= max_items:
                    break
        next_url = _next_link(hdrs.get("link", ""))
    return out[:max_items]


def _next_link(link_header: str) -> str | None:
    # <url>; rel="next", <url>; rel="last"
    for part in link_header.split(","):
        bit = part.strip()
        if 'rel="next"' not in bit and "rel=next" not in bit:
            continue
        if bit.startswith("<") and ">" in bit:
            return bit[1 : bit.index(">")]
    return None


def resolve_targets(
    targets: Sequence[str],
    *,
    max_repos: int = 50,
    token: str | None = None,
) -> list[str]:
    """Expand ``owner/repo`` and bare ``org`` targets into ``owner/repo`` slugs."""
    tok = token if token is not None else _token()
    base = _api_base()
    slugs: list[str] = []
    seen: set[str] = set()
    for raw in targets:
        target = str(raw or "").strip().strip("/")
        if not target:
            continue
        if "/" in target:
            owner, _, repo = target.partition("/")
            slug = f"{owner}/{repo}"
            if slug not in seen:
                seen.add(slug)
                slugs.append(slug)
            if len(slugs) >= max_repos:
                return slugs[:max_repos]
            continue
        # Org or user listing — over-fetch so archived repos do not eat the cap.
        fetch_cap = max(max_repos * 3, max_repos)
        org_url = f"{base}/orgs/{urllib.parse.quote(target)}/repos?type=all&per_page=100"
        try:
            repos = _paginate(org_url, token=tok, max_items=fetch_cap)
        except GitHubAuditError:
            raise
        if not repos:
            user_url = f"{base}/users/{urllib.parse.quote(target)}/repos?type=owner&per_page=100"
            repos = _paginate(user_url, token=tok, max_items=fetch_cap)
        for item in repos:
            if item.get("archived"):
                continue
            full = str(item.get("full_name") or "").strip()
            if not full or full in seen:
                continue
            seen.add(full)
            slugs.append(full)
            if len(slugs) >= max_repos:
                return slugs[:max_repos]
    return slugs[:max_repos]


def _safe_rel_path(path: str) -> str | None:
    """Reject absolute / traversal paths before writing under a temp dir."""
    text = str(path or "").replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    if not text or text.startswith("/") or text.startswith("~"):
        return None
    parts = text.split("/")
    if any(p in {"", ".", ".."} for p in parts):
        return None
    return text


def _fetch_blob_text(
    *,
    owner: str,
    repo: str,
    sha: str,
    token: str | None,
    max_bytes: int,
) -> str | None:
    base = _api_base()
    url = f"{base}/repos/{owner}/{repo}/git/blobs/{sha}"
    data, status, _hdrs = _request_json(
        url,
        token=token,
        accept="application/vnd.github+json",
    )
    if status != 200 or not isinstance(data, dict):
        return None
    size = int(data.get("size") or 0)
    if size > max_bytes:
        return None
    encoding = str(data.get("encoding") or "")
    content = data.get("content")
    if encoding == "base64" and isinstance(content, str):
        raw = base64.b64decode(content)
        if len(raw) > max_bytes:
            return None
        return raw.decode("utf-8", errors="replace")
    if isinstance(content, str):
        return content[:max_bytes]
    return None


def stage_repo_watched_files(
    slug: str,
    *,
    token: str | None = None,
    max_files: int = MAX_WATCHED_FILES_PER_REPO,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    staging_dir: Path | None = None,
) -> tuple[Path, list[str], bool]:
    """Fetch watched blobs into ``staging_dir`` (or a new temp dir).

    Returns ``(root, notes, truncated)``. Caller owns cleanup when
    ``staging_dir`` was provided; otherwise caller must remove the temp dir.
    """
    tok = token if token is not None else _token()
    base = _api_base()
    if "/" not in slug:
        raise GitHubAuditError(f"expected owner/repo, got {slug!r}")
    owner, _, repo = slug.partition("/")
    meta, status, _ = _request_json(f"{base}/repos/{owner}/{repo}", token=tok)
    if status == 404:
        raise GitHubAuditError(f"repository not found: {slug}", status=404)
    if status != 200 or not isinstance(meta, dict):
        raise GitHubAuditError(f"could not load repository metadata for {slug} (HTTP {status})")
    branch = str(meta.get("default_branch") or "") or "main"
    tree_url = (
        f"{base}/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1"
    )
    tree_doc, tstatus, _ = _request_json(tree_url, token=tok)
    if tstatus == 404:
        # Empty repo or missing default branch.
        root = staging_dir or Path(tempfile.mkdtemp(prefix="auctelis-gh-"))
        root.mkdir(parents=True, exist_ok=True)
        return root, [f"{slug}: empty or missing default branch tree"], False
    if tstatus != 200 or not isinstance(tree_doc, dict):
        raise GitHubAuditError(f"could not load git tree for {slug}@{branch} (HTTP {tstatus})")
    truncated = bool(tree_doc.get("truncated"))
    notes: list[str] = []
    if truncated:
        notes.append(f"{slug}: git tree truncated=true — watched-path scan may be incomplete")
    entries = tree_doc.get("tree") or []
    watched: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("type") or "") != "blob":
            continue
        rel = _safe_rel_path(str(entry.get("path") or ""))
        if not rel or not is_watched_path(rel):
            continue
        size = int(entry.get("size") or 0)
        if size > max_file_bytes:
            notes.append(f"{slug}: skipped oversize {rel} ({size} bytes)")
            continue
        watched.append({"path": rel, "sha": str(entry.get("sha") or "")})
        if len(watched) >= max_files:
            notes.append(
                f"{slug}: watched-file cap {max_files} reached — remaining agent paths skipped"
            )
            truncated = True
            break

    root = staging_dir or Path(tempfile.mkdtemp(prefix="auctelis-gh-"))
    root.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for item in watched:
        sha = item["sha"]
        rel = item["path"]
        if not sha:
            continue
        text = _fetch_blob_text(
            owner=owner, repo=repo, sha=sha, token=tok, max_bytes=max_file_bytes
        )
        if text is None:
            notes.append(f"{slug}: failed to fetch blob for {rel}")
            continue
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")
        fetched += 1
    notes.insert(0, f"{slug}: fetched {fetched} watched file(s)")
    return root, notes, truncated


def audit_github_repos(
    targets: Sequence[str],
    *,
    max_repos: int = 50,
    max_files: int | None = None,
    top: int = 5,
    limits: object | None = None,
) -> tuple[list[RepoAuditResult], list[str]]:
    """Audit org/repo targets into ``RepoAuditResult`` rows (temp dirs cleaned)."""
    from auctelis.check import build_check_report

    tok = _token()
    honesty: list[str] = []
    if not tok:
        honesty.append(
            "No GITHUB_TOKEN/GH_TOKEN — using unauthenticated GitHub API "
            "(public repos only; rate limits are lower)."
        )
    try:
        slugs = resolve_targets(targets, max_repos=max_repos, token=tok)
    except GitHubAuditError as exc:
        honesty.append(str(exc))
        return [], honesty
    if not slugs:
        honesty.append("No repositories resolved from --github targets.")
        return [], honesty
    if len(slugs) >= max_repos:
        honesty.append(f"Repository list capped at --max-repos {max_repos}.")

    file_cap = max_files if max_files is not None else MAX_WATCHED_FILES_PER_REPO
    results: list[RepoAuditResult] = []
    for slug in slugs:
        staging: Path | None = None
        try:
            staging, notes, truncated = stage_repo_watched_files(
                slug, token=tok, max_files=file_cap
            )
            report, cards, scan = build_check_report(staging, top=top, limits=limits)
            # Never leak the temp path as the repository label.
            report["repository"] = slug
            if truncated:
                report.setdefault("honesty_notes", [])
                if isinstance(report["honesty_notes"], list):
                    report["honesty_notes"].extend(notes)
            results.append(
                RepoAuditResult(
                    repository=slug,
                    report=report,
                    scan=scan,
                    cards=cards,
                    notes=notes,
                    truncated=truncated,
                )
            )
            honesty.extend(notes)
        except GitHubAuditError as exc:
            results.append(
                RepoAuditResult(
                    repository=slug,
                    skipped=True,
                    notes=[str(exc)],
                )
            )
            honesty.append(f"{slug}: skipped — {exc}")
        except OSError as exc:
            results.append(
                RepoAuditResult(
                    repository=slug,
                    skipped=True,
                    notes=[str(exc)],
                )
            )
            honesty.append(f"{slug}: skipped — {exc}")
        finally:
            if staging is not None:
                _rm_tree(staging)
    return results, honesty


def _rm_tree(path: Path) -> None:
    with contextlib.suppress(OSError):
        shutil.rmtree(path, ignore_errors=True)
