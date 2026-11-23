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

from auctelis.inventory.adapters.mcp import _is_mcp_server_source
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
_AUCTELIS_WORKFLOW_RE = re.compile(
    r"^\.github/workflows/auctelis[^/]*\.ya?ml$",
    re.IGNORECASE,
)
# git@host:owner/repo(.git)?  OR  https://[user[:pass]@]host/owner/repo(.git)?
_GIT_SSH_RE = re.compile(
    r"^(?:ssh://)?git@(?P<host>[^:/]+)[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
_GIT_HTTP_RE = re.compile(
    r"^https?://(?:[^/@]+(?::[^/@]*)?@)?(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
# Set when a successful response reports x-ratelimit-remaining=0 so the *next*
# request short-circuits without discarding the last good payload.
_rate_limit_exhausted: bool = False


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


def _reset_rate_limit_state() -> None:
    """Clear the exhausted flag (tests / start of a fresh audit)."""
    global _rate_limit_exhausted
    _rate_limit_exhausted = False


def _mark_rate_exhausted_from_headers(hdrs: dict[str, str]) -> None:
    """Remember remaining=0 so the next API call fails closed."""
    global _rate_limit_exhausted
    if str(hdrs.get("x-ratelimit-remaining") or "").strip() == "0":
        _rate_limit_exhausted = True


def _is_rate_limited(status: int, hdrs: dict[str, str]) -> bool:
    """True for HTTP 429, or non-200 responses with remaining=0.

    HTTP 200 with remaining=0 still returns the payload; exhaustion is recorded
    for the *next* request via ``_mark_rate_exhausted_from_headers``.
    """
    if status == 429:
        return True
    if status == 200:
        return False
    return str(hdrs.get("x-ratelimit-remaining") or "").strip() == "0"


def _request_json(
    url: str,
    *,
    token: str | None,
    accept: str = "application/vnd.github+json",
) -> tuple[Any | None, int, dict[str, str]]:
    if _rate_limit_exhausted:
        raise GitHubAuditError(
            f"GitHub API rate limit exhausted for {url}",
            status=0,
            rate_limited=True,
        )
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
            status = int(resp.status)
            if _is_rate_limited(status, hdrs):
                raise GitHubAuditError(
                    f"GitHub API rate limit exhausted for {url}",
                    status=status,
                    rate_limited=True,
                )
            # Keep a valid 200 body even when remaining hit 0; short-circuit next.
            _mark_rate_exhausted_from_headers(hdrs)
            if not body:
                return None, status, hdrs
            return json.loads(body.decode("utf-8")), status, hdrs
    except urllib.error.HTTPError as exc:
        hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        # Covers HTTP 429 and non-200 with x-ratelimit-remaining=0 (incl. 403 abuse).
        if _is_rate_limited(exc.code, hdrs):
            _mark_rate_exhausted_from_headers(hdrs)
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
    include_forks: bool = False,
    honesty_notes: list[str] | None = None,
) -> list[str]:
    """Expand ``owner/repo`` and bare ``org`` targets into ``owner/repo`` slugs.

    Org/user listings skip forks by default (pass ``include_forks=True`` to keep
    them). Explicit ``owner/repo`` slugs are never filtered.

    AUCT-031: when falling back to a user listing, authenticated self-targets use
    ``/user/repos`` (private repos included). Other-user / unauthenticated
    listings append a public-only honesty note when ``honesty_notes`` is given.
    """
    # Fresh listing must not inherit exhausted state from a prior audit call.
    _reset_rate_limit_state()
    tok = token if token is not None else _token()
    base = _api_base()
    slugs: list[str] = []
    seen: set[str] = set()
    # Fetch more pages when skipping forks so --max-repos still fills.
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
            repos = _list_user_repos(
                target,
                token=tok,
                max_items=fetch_cap,
                honesty_notes=honesty_notes,
            )
        for item in repos:
            if item.get("archived"):
                continue
            if not include_forks and item.get("fork"):
                continue
            full = str(item.get("full_name") or "").strip()
            if not full or full in seen:
                continue
            seen.add(full)
            slugs.append(full)
            if len(slugs) >= max_repos:
                return slugs[:max_repos]
    return slugs[:max_repos]


def _authenticated_login(token: str | None) -> str | None:
    if not token:
        return None
    data, status, _ = _request_json(f"{_api_base()}/user", token=token)
    if status != 200 or not isinstance(data, dict):
        return None
    login = str(data.get("login") or "").strip()
    return login or None


def _list_user_repos(
    target: str,
    *,
    token: str | None,
    max_items: int,
    honesty_notes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List repos for a user target; prefer ``/user/repos`` for self (AUCT-031)."""
    base = _api_base()
    login = _authenticated_login(token)
    if login and login.lower() == target.lower():
        url = (
            f"{base}/user/repos"
            f"?affiliation=owner&visibility=all&per_page=100&sort=pushed&direction=desc"
        )
        return _paginate(url, token=token, max_items=max_items)
    url = (
        f"{base}/users/{urllib.parse.quote(target)}/repos"
        f"?type=owner&per_page=100&sort=pushed&direction=desc"
    )
    if honesty_notes is not None:
        honesty_notes.append(
            f"/users/{target}/repos lists public repositories only"
            + (" (authenticate as that user to include private repos)." if token else ".")
        )
    return _paginate(url, token=token, max_items=max_items)


def parse_github_remote_url(url: str) -> tuple[str, str] | None:
    """Return ``(web_base, owner/repo)`` from a git remote URL, or ``None``.

    Strips embedded credentials. Supports ``git@host:o/r.git``,
    ``https://host/o/r(.git)``, and GHES hosts.
    """
    text = str(url or "").strip()
    if not text:
        return None
    match = _GIT_SSH_RE.match(text) or _GIT_HTTP_RE.match(text)
    if not match:
        return None
    host = str(match.group("host") or "").strip().lower()
    owner = str(match.group("owner") or "").strip()
    repo = str(match.group("repo") or "").strip()
    if not host or not owner or not repo:
        return None
    slug = f"{owner}/{repo}"
    if not is_owner_repo_slug(slug):
        return None
    if host in {"github.com", "www.github.com"}:
        web_base = "https://github.com"
    else:
        web_base = f"https://{host}"
    return web_base, slug


def infer_local_github_watch_meta(root: Path) -> dict[str, Any]:
    """Best-effort Watch metadata from local ``origin`` + auctelis workflows.

    Non-fatal: returns ``{}`` when git/remote is missing or non-GitHub.
    Only accepts remotes when ``root`` itself is the git toplevel (never
    inherits a parent checkout's ``origin``).
    """
    meta: dict[str, Any] = {}
    resolved = root.expanduser().resolve()
    try:
        top = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return meta
    if top.returncode != 0:
        return meta
    toplevel = Path((top.stdout or "").strip()).resolve()
    if toplevel != resolved:
        return meta
    try:
        proc = subprocess.run(
            ["git", "-C", str(resolved), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return meta
    if proc.returncode != 0:
        return meta
    parsed = parse_github_remote_url((proc.stdout or "").strip())
    if not parsed:
        return meta
    web_base, slug = parsed
    meta["repository"] = slug
    meta["github_web_base"] = web_base
    branch = "main"
    try:
        bproc = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
        if bproc.returncode == 0:
            head = (bproc.stdout or "").strip()
            safe = safe_git_branch(head)
            if head and head != "HEAD" and safe:
                branch = safe
    except (OSError, subprocess.TimeoutExpired):
        pass
    meta["default_branch"] = branch
    wf_dir = resolved / ".github" / "workflows"
    already = False
    if wf_dir.is_dir():
        for path in wf_dir.iterdir():
            if not path.is_file():
                continue
            rel = f".github/workflows/{path.name}".replace("\\", "/")
            if _AUCTELIS_WORKFLOW_RE.match(rel):
                already = True
                break
    meta["already_watching"] = already
    return meta


def safe_git_branch(value: object) -> str | None:
    """Return a safe git/GitHub branch name, or ``None`` if rejected."""
    text = str(value or "").strip()
    if not text or not re.fullmatch(r"[A-Za-z0-9._/-]+", text):
        return None
    if ".." in text or text.startswith("/") or text.endswith("/"):
        return None
    return text


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
) -> tuple[Path, list[str], bool, dict[str, Any]]:
    """Fetch watched blobs into ``staging_dir`` (or a new temp dir).

    Returns ``(root, notes, truncated, meta)`` where ``meta`` includes
    ``default_branch``, ``github_web_base``, and ``already_watching``.
    Caller owns cleanup when ``staging_dir`` was provided; otherwise caller
    must remove the temp dir.
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
    meta: dict[str, Any] = {
        "default_branch": branch,
        "github_web_base": web_base,
        "already_watching": False,
    }
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
    already_watching = False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("type") or "") != "blob":
            continue
        rel = _safe_rel_path(str(entry.get("path") or ""))
        if not rel:
            continue
        if _AUCTELIS_WORKFLOW_RE.match(rel):
            already_watching = True
        if not is_watched_path(rel):
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

    meta["already_watching"] = already_watching
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


def stage_repo_inspect_files(
    slug: str,
    *,
    token: str | None = None,
    max_files: int = 100,
    staging_dir: Path | None = None,
) -> tuple[Path, list[str], bool, dict[str, Any]]:
    """Fetch inspect blobs (watched + manifest + MCP server source) into staging.

    Mirrors ``stage_repo_watched_files`` with a broader path predicate.
    """
    max_file_bytes = DEFAULT_MAX_FILE_BYTES
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
    meta: dict[str, Any] = {
        "default_branch": branch,
        "github_web_base": web_base,
        "already_watching": False,
    }
    tree_url = (
        f"{base}/repos/{owner}/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1"
    )
    tree_doc, tstatus, _ = _request_json(tree_url, token=tok)
    if tstatus == 404:
        root = staging_dir or Path(tempfile.mkdtemp(prefix="auctelis-gh-"))
        root.mkdir(parents=True, exist_ok=True)
        return root, [f"{slug}: empty or missing default branch tree"], False, meta
    if tstatus != 200 or not isinstance(tree_doc, dict):
        raise GitHubAuditError(f"could not load git tree for {slug}@{branch} (HTTP {tstatus})")
    truncated = bool(tree_doc.get("truncated"))
    notes: list[str] = []
    if truncated:
        notes.append(f"{slug}: git tree truncated=true — inspect-path scan may be incomplete")
    entries = tree_doc.get("tree") or []
    selected: list[dict[str, Any]] = []
    already_watching = False
    _manifest_names = {"package.json", "pyproject.toml", "setup.py"}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("type") or "") != "blob":
            continue
        rel = _safe_rel_path(str(entry.get("path") or ""))
        if not rel:
            continue
        if _AUCTELIS_WORKFLOW_RE.match(rel):
            already_watching = True
        name = Path(rel).name
        if not (
            is_watched_path(rel) or name in _manifest_names or _is_mcp_server_source(Path(rel))
        ):
            continue
        size = int(entry.get("size") or 0)
        if size > max_file_bytes:
            notes.append(f"{slug}: skipped oversize {rel} ({size} bytes)")
            continue
        selected.append({"path": rel, "sha": str(entry.get("sha") or "")})
        if len(selected) >= max_files:
            notes.append(f"{slug}: inspect-file cap {max_files} reached — remaining paths skipped")
            truncated = True
            break

    meta["already_watching"] = already_watching
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

    if selected:
        with ThreadPoolExecutor(max_workers=_BLOB_WORKERS) as pool:
            futures = [pool.submit(_one, item) for item in selected]
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
    notes.insert(0, f"{slug}: fetched {fetched} inspect file(s)")
    return root, notes, truncated, meta


def audit_github_repos(
    targets: Sequence[str],
    *,
    max_repos: int = 50,
    max_files: int | None = None,
    top: int = 5,
    limits: object | None = None,
    include_forks: bool = False,
) -> tuple[list[RepoAuditResult], list[str]]:
    """Audit org/repo targets into ``RepoAuditResult`` rows (temp dirs cleaned)."""
    from auctelis.check import build_check_report

    _reset_rate_limit_state()
    tok = _token()
    honesty: list[str] = []
    if not tok:
        honesty.append(
            "No GITHUB_TOKEN/GH_TOKEN/gh auth — using unauthenticated GitHub API "
            "(public repos only; rate limits are lower)."
        )
    try:
        slugs = resolve_targets(
            targets,
            max_repos=max_repos,
            token=tok,
            include_forks=include_forks,
            honesty_notes=honesty,
        )
    except GitHubAuditError as exc:
        honesty.append(str(exc))
        return [], honesty
    if not slugs:
        honesty.append("No repositories resolved from --github targets.")
        if not include_forks:
            honesty.append("Forks are skipped by default; pass --include-forks to include them.")
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
            report["already_watching"] = bool(meta.get("already_watching"))
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
