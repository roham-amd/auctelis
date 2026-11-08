"""Dependency check/upgrade helpers backed by uv.lock."""

from __future__ import annotations

import json
import subprocess
import tomllib
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version

from authdiff.paths import repo_root

_PYPI = "https://pypi.org/pypi/{name}/json"
_USER_AGENT = "authdiff-deps/0.3 (+https://github.com/YOUR_GITHUB_ORG/authdiff)"


@dataclass(frozen=True, slots=True)
class PinStatus:
    name: str
    current: str
    latest: str
    outdated: bool
    error: str | None = None


def tools_dir() -> Path:
    return repo_root() / "tools"


def lock_path() -> Path:
    return tools_dir() / "uv.lock"


def pyproject_path() -> Path:
    return tools_dir() / "pyproject.toml"


def parse_lock_pins(text: str | None = None) -> dict[str, str]:
    """Return ``name -> version`` for every package entry in ``uv.lock``."""
    raw = text if text is not None else lock_path().read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    pins: dict[str, str] = {}
    for package in data.get("package", []):
        name = package.get("name")
        version = package.get("version")
        if isinstance(name, str) and isinstance(version, str):
            pins[name] = version
    return pins


def parse_declared_requirements(text: str | None = None) -> list[Requirement]:
    """Runtime + PEP 735 dependency-group requirements from ``pyproject.toml``."""
    raw = text if text is not None else pyproject_path().read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    declared: list[str] = []
    project = data.get("project") or {}
    declared.extend(str(item) for item in project.get("dependencies") or [])
    groups = data.get("dependency-groups") or {}
    for entries in groups.values():
        if isinstance(entries, list):
            declared.extend(str(item) for item in entries if isinstance(item, str))
    return [Requirement(item) for item in declared]


def fetch_latest_version(name: str, *, timeout: float = 20.0) -> str:
    req = urllib.request.Request(
        _PYPI.format(name=name),
        headers={"Accept": "application/json", "User-Agent": _USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    version = payload.get("info", {}).get("version")
    if not version:
        raise RuntimeError(f"PyPI response for {name} missing info.version")
    return str(version)


def _is_outdated(current: str, latest: str) -> bool:
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        return current != latest


def _resolve_pin_name(pins: dict[str, str], name: str) -> tuple[str, str] | None:
    if name in pins:
        return name, pins[name]
    match = next((key for key in pins if key.lower() == name.lower()), None)
    if match is None:
        return None
    return match, pins[match]


def check_outdated(*, packages: list[str] | None = None) -> list[PinStatus]:
    pins = parse_lock_pins()
    names = packages or sorted(pins.keys(), key=str.lower)
    results: list[PinStatus] = []
    for name in names:
        resolved = _resolve_pin_name(pins, name)
        if resolved is None:
            results.append(
                PinStatus(
                    name=name,
                    current="",
                    latest="",
                    outdated=False,
                    error="not in uv.lock",
                )
            )
            continue
        canon, current = resolved
        try:
            latest = fetch_latest_version(canon)
            results.append(
                PinStatus(
                    name=canon,
                    current=current,
                    latest=latest,
                    outdated=_is_outdated(current, latest),
                )
            )
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            results.append(
                PinStatus(
                    name=canon,
                    current=current,
                    latest="",
                    outdated=False,
                    error=str(exc),
                )
            )
    return results


def _uv_executable() -> str:
    """Resolve uv even when the install directory is not on PATH (common on Windows)."""
    import shutil
    from pathlib import Path

    found = shutil.which("uv")
    if found:
        return found
    candidates = [
        Path.home() / ".local" / "bin" / "uv.exe",
        Path.home() / ".local" / "bin" / "uv",
        Path.home() / ".cargo" / "bin" / "uv.exe",
        Path.home() / ".cargo" / "bin" / "uv",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return "uv"


def _run_uv(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_uv_executable(), *args],
        cwd=tools_dir(),
        check=False,
        text=True,
        capture_output=True,
    )


def upgrade_pins(
    *,
    dry_run: bool = False,
    requires_python: str = ">=3.12",
    as_of: date | None = None,
) -> dict[str, Any]:
    """Bump locked deps via ``uv lock --upgrade`` (constraints stay in pyproject.toml)."""
    as_of = as_of or date.today()
    statuses = check_outdated()
    errors = [status for status in statuses if status.error]
    if errors:
        return {
            "ok": False,
            "dry_run": dry_run,
            "errors": [asdict(err) for err in errors],
            "updated": [],
        }

    changed = [
        {"name": status.name, "from": status.current, "to": status.latest}
        for status in statuses
        if status.outdated or status.current != status.latest
    ]

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "requires_python": requires_python,
            "as_of": as_of.isoformat(),
            "updated": changed,
            "pins": {status.name: status.latest for status in statuses},
            "command": "uv lock --upgrade",
        }

    proc = _run_uv(["lock", "--upgrade"])
    if proc.returncode != 0:
        return {
            "ok": False,
            "dry_run": False,
            "errors": [
                {
                    "name": "uv",
                    "current": "",
                    "latest": "",
                    "outdated": False,
                    "error": (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip(),
                }
            ],
            "updated": [],
        }

    return {
        "ok": True,
        "dry_run": False,
        "requires_python": requires_python,
        "as_of": as_of.isoformat(),
        "updated": changed,
        "pins": parse_lock_pins(),
        "command": "uv lock --upgrade",
    }


def outdated_report() -> dict[str, Any]:
    statuses = check_outdated()
    outdated = [asdict(status) for status in statuses if status.outdated]
    errors = [asdict(status) for status in statuses if status.error]
    return {
        "checked": len(statuses),
        "outdated_count": len(outdated),
        "outdated": outdated,
        "errors": errors,
        "all": [asdict(status) for status in statuses],
        "requires_python_expected": ">=3.12",
        "lock": str(lock_path().relative_to(repo_root()).as_posix()),
    }


def ensure_lock_in_sync() -> None:
    """Fail if ``uv.lock`` is missing or out of sync with ``pyproject.toml``."""
    path = lock_path()
    if not path.is_file():
        raise SystemExit(f"Missing lockfile: {path} (run: cd tools && uv lock)")
    proc = _run_uv(["lock", "--check"])
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "uv.lock is out of date").strip()
        raise SystemExit(f"uv.lock out of sync with pyproject.toml: {detail}")
