"""Opt-in npm/PyPI pin resolution (AUCT-050).

Looks up the latest published version via registry JSON APIs. Never executes
packages. Docker/Podman digests stay placeholders. Callers inject a fetcher in
tests; production uses stdlib ``urllib`` with a 5s timeout.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from auctelis.authority_lock import _normalize_package_stem
from auctelis.textutil import validated_http_url

_TIMEOUT_S = 5.0
_USER_AGENT = "auctelis-pin-resolve"
_NPM = "https://registry.npmjs.org"
_PYPI = "https://pypi.org/pypi"

Fetcher = Callable[[str], tuple[int, Any]]


def _default_fetcher(url: str) -> tuple[int, Any]:
    safe = validated_http_url(url, what="registry URL")
    req = urllib.request.Request(
        safe,
        headers={"Accept": "application/json", "User-Agent": _USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # nosec B310
            raw = resp.read()
            status = int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        status = int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, None
    if not raw:
        return status, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None


def fetch_npm_latest(package: str, *, fetcher: Fetcher | None = None) -> str | None:
    """Return npm ``dist-tags.latest`` for ``package``, or ``None`` on failure."""
    name = str(package or "").strip()
    if not name:
        return None
    # Scoped packages: @scope/name → /@scope%2Fname
    encoded = urllib.parse.quote(name, safe="@")
    if name.startswith("@") and "/" in name:
        scope, _, pkg = name[1:].partition("/")
        encoded = f"@{urllib.parse.quote(scope)}%2F{urllib.parse.quote(pkg)}"
    url = f"{_NPM}/{encoded}"
    status, body = (fetcher or _default_fetcher)(url)
    if status != 200 or not isinstance(body, dict):
        return None
    tags = body.get("dist-tags")
    if not isinstance(tags, dict):
        return None
    latest = str(tags.get("latest") or "").strip()
    return latest or None


def fetch_pypi_latest(package: str, *, fetcher: Fetcher | None = None) -> str | None:
    """Return PyPI ``info.version`` for ``package``, or ``None`` on failure."""
    name = str(package or "").strip()
    if not name:
        return None
    url = f"{_PYPI}/{urllib.parse.quote(name)}/json"
    status, body = (fetcher or _default_fetcher)(url)
    if status != 200 or not isinstance(body, dict):
        return None
    info = body.get("info")
    if not isinstance(info, dict):
        return None
    version = str(info.get("version") or "").strip()
    return version or None


def _package_stem_from_item(item: dict[str, Any]) -> str:
    snippet = str(item.get("config_snippet") or "")
    suggestion = str(item.get("suggestion") or "")
    for text in (snippet, suggestion):
        # Prefer a token that still carries the placeholder suffix.
        for marker in ("@<exact-version>", "==<exact-version>"):
            if marker not in text:
                continue
            # Pull the last quoted or whitespace-delimited token containing the marker.
            for part in text.replace(",", " ").replace('"', " ").split():
                if marker not in part:
                    continue
                cleaned = part.replace(marker, "").strip("[](){}<>'")
                stem = _normalize_package_stem(cleaned)
                if stem:
                    return stem
    return ""


def _resolved_token(launch: str, stem: str, version: str) -> str:
    if launch in {"npx", "bunx"}:
        return f"{stem}@{version}"
    if launch in {"uvx", "pipx"}:
        return f"{stem}=={version}"
    return stem


def _apply_version_to_snippet(snippet: str, launch: str, version: str) -> str:
    if not snippet or not version:
        return snippet
    if launch in {"npx", "bunx"}:
        return snippet.replace("@<exact-version>", f"@{version}")
    if launch in {"uvx", "pipx"}:
        return snippet.replace("==<exact-version>", f"=={version}")
    return snippet


def resolve_pin_item(
    item: dict[str, Any],
    *,
    fetcher: Fetcher | None = None,
    now: datetime | None = None,
) -> bool:
    """Mutate one pins item with ``resolved_pin`` / ``resolved_at`` when possible.

    Returns True when a concrete version was attached. Docker/Podman and lookup
    failures leave the item unchanged (placeholder stays).
    """
    launch = str(item.get("launcher") or "").lower().removesuffix(".exe").removesuffix(".cmd")
    if launch in {"docker", "podman"}:
        return False
    if launch not in {"npx", "bunx", "uvx", "pipx"}:
        return False
    stem = _package_stem_from_item(item)
    if not stem:
        return False
    if launch in {"npx", "bunx"}:
        version = fetch_npm_latest(stem, fetcher=fetcher)
    else:
        version = fetch_pypi_latest(stem, fetcher=fetcher)
    if not version:
        return False
    stamp = now or datetime.now(UTC)
    resolved_at = stamp.astimezone(UTC).strftime("%Y-%m-%d")
    token = _resolved_token(launch, stem, version)
    snippet = str(item.get("config_snippet") or "")
    item["resolved_pin"] = token
    item["resolved_at"] = resolved_at
    item["resolved_config_snippet"] = _apply_version_to_snippet(snippet, launch, version)
    suggestion = str(item.get("suggestion") or "")
    if suggestion:
        item["resolved_suggestion"] = _apply_version_to_snippet(suggestion, launch, version)
    return True


def resolve_pins_document(
    pins: dict[str, Any] | None,
    *,
    fetcher: Fetcher | None = None,
    now: datetime | None = None,
) -> int:
    """Resolve every item in a ``pins`` document. Returns count resolved."""
    if not isinstance(pins, dict):
        return 0
    items = pins.get("items")
    if not isinstance(items, list):
        return 0
    count = 0
    for item in items:
        if isinstance(item, dict) and resolve_pin_item(item, fetcher=fetcher, now=now):
            count += 1
    return count


def resolve_pins_in_report(
    report: dict[str, Any],
    *,
    fetcher: Fetcher | None = None,
    now: datetime | None = None,
) -> int:
    """Resolve pins on a single-repo check/report or each fleet repository."""
    total = 0
    repos = report.get("repositories")
    if isinstance(repos, list):
        for repo in repos:
            if isinstance(repo, dict):
                pins = repo.get("pins")
                if isinstance(pins, dict):
                    total += resolve_pins_document(pins, fetcher=fetcher, now=now)
        return total
    pins = report.get("pins")
    if isinstance(pins, dict):
        total += resolve_pins_document(pins, fetcher=fetcher, now=now)
    return total
