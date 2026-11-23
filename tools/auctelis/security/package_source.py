"""Non-executing package archive extraction (AUCT-063).

Reads text sources from npm tarballs and PyPI wheels/sdists without
installing or running package code.
"""

from __future__ import annotations

import io
import tarfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from auctelis.textutil import validated_http_url

MAX_ARCHIVE_BYTES = 5_242_880
MAX_ARCHIVE_FILES = 60
MAX_MEMBER_BYTES = 262_144
SOURCE_SUFFIXES = (".py", ".ts", ".js", ".mjs", ".json", ".toml", ".md")

_TIMEOUT_S = 10.0
_USER_AGENT = "auctelis-package-source"

Fetcher = Callable[[str], bytes]


def _safe_member_name(name: str) -> str | None:
    raw = str(name or "").replace("\\", "/")
    if not raw or raw.startswith("/") or ".." in raw.split("/"):
        return None
    if raw.startswith("package/"):
        raw = raw[len("package/") :]
    if not raw or raw.startswith("/") or ".." in raw.split("/"):
        return None
    return raw


def _is_source_path(rel: str) -> bool:
    lower = rel.lower()
    return any(lower.endswith(suf) for suf in SOURCE_SUFFIXES)


def extract_archive_text_files(
    archive_bytes: bytes, *, kind: Literal["tar.gz", "zip"]
) -> dict[str, str]:
    """Extract text source members from an in-memory archive (no execution)."""
    out: dict[str, str] = {}
    if kind == "tar.gz":
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tf:
            for member in tf.getmembers():
                if len(out) >= MAX_ARCHIVE_FILES:
                    break
                if member.issym() or member.islnk() or not member.isfile():
                    continue
                if member.size > MAX_MEMBER_BYTES:
                    continue
                rel = _safe_member_name(member.name)
                if rel is None or not _is_source_path(rel):
                    continue
                extracted = tf.extractfile(member)
                if extracted is None:
                    continue
                data = extracted.read(MAX_MEMBER_BYTES + 1)
                if len(data) > MAX_MEMBER_BYTES:
                    continue
                out[rel] = data.decode("utf-8", errors="replace")
        return out

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
        for info in zf.infolist():
            if len(out) >= MAX_ARCHIVE_FILES:
                break
            # Skip directories and Unix symlinks (external_attr high bits == 0o120000).
            if info.is_dir():
                continue
            is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                continue
            if info.file_size > MAX_MEMBER_BYTES:
                continue
            rel = _safe_member_name(info.filename)
            if rel is None or not _is_source_path(rel):
                continue
            data = zf.read(info)[: MAX_MEMBER_BYTES + 1]
            if len(data) > MAX_MEMBER_BYTES:
                continue
            out[rel] = data.decode("utf-8", errors="replace")
    return out


def stage_archive_to_dir(files: dict[str, str], dest: Path) -> int:
    """Write extracted text files under ``dest``; refuse path escape."""
    root = dest.resolve()
    root.mkdir(parents=True, exist_ok=True)
    written = 0
    for rel, text in files.items():
        safe = _safe_member_name(rel)
        if safe is None:
            continue
        target = dest / safe
        resolved = target.resolve()
        assert resolved.is_relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        written += 1
    return written


def _default_fetcher(url: str) -> bytes:
    safe = validated_http_url(url, what="package archive URL")
    req = urllib.request.Request(
        safe,
        headers={"User-Agent": _USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # nosec B310
        return bytes(resp.read(MAX_ARCHIVE_BYTES + 1))


def fetch_package_archive(
    eco: Literal["npm", "pypi"],
    meta: dict[str, Any],
    *,
    fetcher: Fetcher | None = None,
) -> tuple[bytes | None, Literal["tar.gz", "zip"] | None]:
    """Fetch an npm tarball or PyPI wheel/sdist bytes. Never executes the package."""
    get = fetcher or _default_fetcher
    url: str | None = None
    kind: Literal["tar.gz", "zip"] | None = None
    try:
        if eco == "npm":
            dist = meta.get("dist") or {}
            if not isinstance(dist, dict):
                return None, None
            raw_url = dist.get("tarball")
            if not isinstance(raw_url, str) or not raw_url.strip():
                return None, None
            url = validated_http_url(raw_url, what="npm tarball URL")
            kind = "tar.gz"
        else:
            urls = meta.get("urls") or []
            if not isinstance(urls, list):
                return None, None
            wheel_url: str | None = None
            sdist_url: str | None = None
            for u in urls:
                if not isinstance(u, dict):
                    continue
                u_url = u.get("url")
                if not isinstance(u_url, str) or not u_url.strip():
                    continue
                ptype = str(u.get("packagetype") or "")
                if ptype == "bdist_wheel" and wheel_url is None:
                    wheel_url = u_url
                elif ptype == "sdist" and u_url.endswith(".tar.gz") and sdist_url is None:
                    sdist_url = u_url
            if wheel_url is not None:
                url = validated_http_url(wheel_url, what="PyPI wheel URL")
                kind = "zip"
            elif sdist_url is not None:
                url = validated_http_url(sdist_url, what="PyPI sdist URL")
                kind = "tar.gz"
            else:
                return None, None

        data = get(url)
        if not isinstance(data, (bytes, bytearray)) or len(data) > MAX_ARCHIVE_BYTES:
            return None, None
        return bytes(data), kind
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
        return None, None
