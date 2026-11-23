"""Immutable Action pin helpers shared by ``init --pin-sha`` / ``--action-sha``."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from auctelis.github_audit import _api_base, _token
from auctelis.textutil import validated_http_url

_USER_AGENT = "auctelis-rollout"
_API_VERSION = "2022-11-28"
_ACTION_SLUG = "roham-amd/auctelis"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_LOCKLESS_TAG_RE = re.compile(r"(uses:\s*roham-amd/auctelis@)v[^\s#]+")


def resolve_release_commit_sha(version: str) -> tuple[str | None, str]:
    """Resolve ``roham-amd/auctelis`` tag ``v<version>`` to a commit SHA.

    Lightweight tags return the commit directly. Annotated tags
    (``object.type == "tag"``) are dereferenced with ``GET /git/tags/<sha>``.
    """
    token = _token()
    ref = f"v{version}"
    status, body = _request(
        "GET",
        _repo_api(_ACTION_SLUG, f"/git/ref/tags/{urllib.parse.quote(ref, safe='')}"),
        token=token,
    )
    if status != 200 or not isinstance(body, dict):
        return None, f"HTTP {status} on tags/{ref}"
    obj = body.get("object")
    if not isinstance(obj, dict):
        return None, f"tags/{ref} response missing object"
    sha = str(obj.get("sha") or "").lower()
    kind = str(obj.get("type") or "")
    if kind == "tag":
        status, tag_body = _request(
            "GET",
            _repo_api(_ACTION_SLUG, f"/git/tags/{urllib.parse.quote(sha, safe='')}"),
            token=token,
        )
        if status != 200 or not isinstance(tag_body, dict):
            return None, f"HTTP {status} on git/tags/{sha}"
        inner = tag_body.get("object")
        if not isinstance(inner, dict):
            return None, "annotated tag missing object"
        if str(inner.get("type") or "") != "commit":
            return None, f"annotated tag object type {inner.get('type')!r} is not commit"
        sha = str(inner.get("sha") or "").lower()
    elif kind != "commit":
        return None, f"tag object type {kind!r} is not commit or tag"
    if _SHA40.fullmatch(sha) is None:
        return None, "resolved object is not a 40-character commit SHA"
    return sha, ""


def normalize_action_sha(raw: str) -> tuple[str | None, str]:
    """Accept a 40-hex commit SHA (any case) and return it lowercase."""
    sha = raw.strip().lower()
    if _SHA40.fullmatch(sha) is None:
        return None, "must be a 40-character hex commit SHA"
    return sha, ""


def rewrite_action_pin(workflow: str, *, sha: str, version: str) -> str:
    """Replace the mutable ``@vX`` Action pin with ``@<sha> # vX``.

    Shared by lockless Watch templates and enforce ``auctelis-gate.yml``
    (AUCT-057).
    """
    updated, count = _LOCKLESS_TAG_RE.subn(rf"\g<1>{sha} # v{version}", workflow, count=1)
    if count != 1:
        raise ValueError("workflow has no roham-amd/auctelis@v pin")
    return updated


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
