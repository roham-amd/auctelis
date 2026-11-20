"""Zero-clone GitHub org/repo Reach Audit via Trees + Blobs API (AUCT-022/025/026).

Uses stdlib ``urllib`` only. Fetches watched agent-config paths into a temp
directory, runs the normal check inventory, and never clones a git repo.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
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
_BLOB_WORKERS = 6
_OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GitHubAuditError(Exception):
    """Honest fail for auth, rate-limit, or unreachable GitHub API."""

    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        rate_limited: bool = False,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.rate_limited = rate_limited


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


def _github_web_base() -> str:
    """Public GitHub or GHES web origin for ``/new/`` PR-Watch links."""
    server = (os.environ.get("GITHUB_SERVER_URL") or "").rstrip("/")
    if server:
        return server
    api = _api_base()
    if api == "https://api.github.com" or api.endswith("://api.github.com"):
        return "https://github.com"
    if api.endswith("/api/v3"):
        return api[: -len("/api/v3")]
    if api.endswith("/api"):
        return api[: -len("/api")]
    return api


def _token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok and tok.strip():
        return tok.strip()
    try:
        proc = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None


def _is_rate_limited(status: int, hdrs: dict[str, str]) -> bool:
    """True when GitHub signals exhaustion (remaining=0 or HTTP 429)."""
    if str(hdrs.get("x-ratelimit-remaining") or "").strip() == "0":
        return True
    return status == 429


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
            if _is_rate_limited(int(resp.status), hdrs):
                raise GitHubAuditError(
                    f"GitHub API rate limit exhausted for {url}",
                    status=int(resp.status),
                    rate_limited=True,
                )
            if not body:
                return None, int(resp.status), hdrs
            return json.loads(body.decode("utf-8")), int(resp.status), hdrs
    except urllib.error.HTTPError as exc:
        hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        if _is_rate_limited(exc.code, hdrs) or exc.code == 429:
            raise GitHubAuditError(
                f"GitHub API HTTP {exc.code} (rate limit) for {url}",
                status=exc.code,
                rate_limited=True,
            ) from exc
        if exc.code == 401:
            raise GitHubAuditError(
                f"GitHub API HTTP {exc.code} (unauthorized) for {url}",
                status=exc.code,
            ) from exc
        if exc.code == 403:
            raise GitHubAuditError(
                f"GitHub API HTTP {exc.code} (forbidden) for {url}",
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
        # Org or user listing — most recently pushed first so the cap hits active repos.
        fetch_cap = max(max_repos * 3, max_repos)
        org_url = (
            f"{base}/orgs/{urllib.parse.quote(target)}/repos"
            f"?type=all&per_page=100&sort=pushed&direction=desc"
        )
        try:
            repos = _paginate(org_url, token=tok, max_items=fetch_cap)
        except GitHubAuditError:
            raise
        if not repos:
            user_url = (
                f"{base}/users/{urllib.parse.quote(target)}/repos"
                f"?type=owner&per_page=100&sort=pushed&direction=desc"
            )
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
) -> tuple[Path, list[str], bool, dict[str, str]]:
    """Fetch watched blobs into ``staging_dir`` (or a new temp dir).

    Returns ``(root, notes, truncated, meta)`` where ``meta`` includes
    ``default_branch`` and ``github_web_base``. Caller owns cleanup when
    ``staging_dir`` was provided; otherwise caller must remove the temp dir.
    """
    tok = token if token is not None else _token()
    base = _api_base()
    web_base = _github_web_base()
    if "/" not in slug:
        raise GitHubAuditError(f"expected owner/repo, got {slug!r}")
    owner, _, repo = slug.partition("/")
    meta_doc, status, _ = _request_json(f"{base}/repos/{owner}/{repo}", token=tok)
    if status == 404:
        raise GitHubAuditError(f"repository not found: {slug}", status=404)
    if status != 200 or not isinstance(meta_doc, dict):
        raise GitHubAuditError(f"could not load repository metadata for {slug} (HTTP {status})")
    branch = str(meta_doc.get("default_branch") or "") or "main"
    meta = {"default_branch": branch, "github_web_base": web_base}
    tree_url = (
        f"{base}/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1"
    )
    tree_doc, tstatus, _ = _request_json(tree_url, token=tok)
    if tstatus == 404:
        # Empty repo or missing default branch.
        root = staging_dir or Path(tempfile.mkdtemp(prefix="auctelis-gh-"))
        root.mkdir(parents=True, exist_ok=True)
        return root, [f"{slug}: empty or missing default branch tree"], False, meta
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

    def _one(item: dict[str, Any]) -> tuple[str, str | None, str | None]:
        sha = item["sha"]
        rel = item["path"]
        if not sha:
            return rel, None, "missing sha"
        try:
            text = _fetch_blob_text(
                owner=owner, repo=repo, sha=sha, token=tok, max_bytes=max_file_bytes
            )
        except GitHubAuditError:
            raise
        if text is None:
            return rel, None, f"failed to fetch blob for {rel}"
        return rel, text, None

    if watched:
        with ThreadPoolExecutor(max_workers=_BLOB_WORKERS) as pool:
            futures = [pool.submit(_one, item) for item in watched]
            for fut in as_completed(futures):
                try:
                    rel, text, err = fut.result()
                except GitHubAuditError:
                    for pending in futures:
                        pending.cancel()
                    raise
                if err:
                    notes.append(f"{slug}: {err}")
                    continue
                if text is None:
                    continue
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8", newline="\n")
                fetched += 1
    notes.insert(0, f"{slug}: fetched {fetched} watched file(s)")
    return root, notes, truncated, meta


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
            "No GITHUB_TOKEN/GH_TOKEN/gh auth — using unauthenticated GitHub API "
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
    abort_note = "GitHub API rate limit exhausted — remaining repositories skipped."
    for index, slug in enumerate(slugs):
        staging: Path | None = None
        try:
            staging, notes, truncated, meta = stage_repo_watched_files(
                slug, token=tok, max_files=file_cap
            )
            report, cards, scan = build_check_report(staging, top=top, limits=limits)
            # Never leak the temp path as the repository label.
            report["repository"] = slug
            report["default_branch"] = meta.get("default_branch") or "main"
            report["github_web_base"] = meta.get("github_web_base") or _github_web_base()
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
            if exc.rate_limited:
                honesty.append(abort_note)
                for rest in slugs[index + 1 :]:
                    results.append(
                        RepoAuditResult(
                            repository=rest,
                            skipped=True,
                            notes=[abort_note],
                        )
                    )
                break
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


def is_owner_repo_slug(value: object) -> bool:
    """True when ``value`` looks like a safe ``owner/repo`` GitHub slug."""
    text = str(value or "").strip()
    return bool(_OWNER_REPO_RE.fullmatch(text))


def _rm_tree(path: Path) -> None:
    with contextlib.suppress(OSError):
        shutil.rmtree(path, ignore_errors=True)
