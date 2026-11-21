"""AUCT-022: zero-clone GitHub org/repo fleet Reach Audit."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from auctelis.github_audit import (
    GitHubAuditError,
    audit_github_repos,
    resolve_targets,
    stage_repo_watched_files,
)
from auctelis.inventory.watched_paths import is_watched_path


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200, headers: dict[str, str] | None = None):
        self._payload = payload
        self.status = status
        self.headers = headers or {}

    def read(self) -> bytes:
        if isinstance(self._payload, (bytes, bytearray)):
            return bytes(self._payload)
        if self._payload is None:
            return b""
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _install_http(monkeypatch: pytest.MonkeyPatch, routes: dict[str, Any]) -> list[str]:
    """Map URL → payload or (payload, status, headers). Longest-prefix wins."""
    from auctelis import github_audit

    github_audit._reset_rate_limit_state()
    seen: list[str] = []

    def opener(req: Request, timeout: float = 0):
        url = req.full_url
        seen.append(url)
        hit = None
        best = -1
        for key, value in routes.items():
            if (url == key or url.startswith(key)) and len(key) > best:
                hit = value
                best = len(key)
        if hit is None:
            raise HTTPError(url, 404, "not found", hdrs=None, fp=None)  # type: ignore[arg-type]
        if isinstance(hit, tuple):
            payload, status, headers = hit
        else:
            payload, status, headers = hit, 200, {}
        if status >= 400:
            raise HTTPError(url, status, "error", hdrs=headers, fp=None)  # type: ignore[arg-type]
        return _FakeResponse(payload, status=status, headers=headers)

    monkeypatch.setattr("urllib.request.urlopen", opener)
    return seen


def test_is_watched_path_filters_agent_configs_only():
    assert is_watched_path(".cursor/mcp.json")
    assert is_watched_path(".github/instructions/api.instructions.md")
    assert is_watched_path(".windsurf/rules/sec.md")
    assert not is_watched_path("src/app.py")
    assert not is_watched_path("../etc/passwd")
    assert not is_watched_path("/abs/path")


def test_resolve_targets_org_pagination_and_max_repos(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    page1 = [
        {"full_name": "acme/one", "archived": False},
        {"full_name": "acme/two", "archived": True},
        {"full_name": "acme/three", "archived": False},
    ]
    routes = {
        "https://api.github.com/orgs/acme/repos": (
            page1,
            200,
            {"Link": ""},
        ),
    }
    seen = _install_http(monkeypatch, routes)
    slugs = resolve_targets(["acme"], max_repos=2)
    assert slugs == ["acme/one", "acme/three"][:2]
    assert len(slugs) == 2
    assert any("sort=pushed" in u and "direction=desc" in u for u in seen)


def test_resolve_targets_owner_repo_passthrough(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    seen = _install_http(monkeypatch, {})
    slugs = resolve_targets(["acme/app", "acme/other"], max_repos=50)
    assert slugs == ["acme/app", "acme/other"]
    assert seen == []


def test_stage_repo_fetches_only_watched_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    mcp = json.dumps({"mcpServers": {"x": {"command": "npx", "args": ["-y", "demo"]}}})
    tree = {
        "truncated": False,
        "tree": [
            {"path": "README.md", "type": "blob", "sha": "sha-readme", "size": 10},
            {"path": ".cursor/mcp.json", "type": "blob", "sha": "sha-mcp", "size": len(mcp)},
            {"path": "src/main.py", "type": "blob", "sha": "sha-src", "size": 20},
        ],
    }
    routes = {
        "https://api.github.com/repos/acme/app": {"default_branch": "main"},
        "https://api.github.com/repos/acme/app/git/trees/main": tree,
        "https://api.github.com/repos/acme/app/git/blobs/sha-mcp": {
            "encoding": "base64",
            "content": _b64(mcp),
            "size": len(mcp),
        },
    }
    seen = _install_http(monkeypatch, routes)
    staging = tmp_path / "stage"
    root, notes, truncated, meta = stage_repo_watched_files(
        "acme/app", staging_dir=staging, max_files=100
    )
    assert root == staging
    assert not truncated
    assert meta["default_branch"] == "main"
    assert meta["github_web_base"] == "https://github.com"
    assert (staging / ".cursor" / "mcp.json").is_file()
    assert not (staging / "README.md").exists()
    assert not (staging / "src" / "main.py").exists()
    assert any("fetched 1" in n for n in notes)
    assert not any("sha-readme" in u for u in seen)
    assert not any("sha-src" in u for u in seen)


def test_stage_repo_rejects_traversal_and_reports_truncated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("GH_TOKEN", "tok")
    tree = {
        "truncated": True,
        "tree": [
            {"path": "../evil", "type": "blob", "sha": "bad", "size": 1},
            {"path": ".cursorrules", "type": "blob", "sha": "sha-rules", "size": 4},
        ],
    }
    routes = {
        "https://api.github.com/repos/acme/app": {"default_branch": "main"},
        "https://api.github.com/repos/acme/app/git/trees/main": tree,
        "https://api.github.com/repos/acme/app/git/blobs/sha-rules": {
            "encoding": "base64",
            "content": _b64("ok\n"),
            "size": 4,
        },
    }
    _install_http(monkeypatch, routes)
    root, notes, truncated, meta = stage_repo_watched_files(
        "acme/app", staging_dir=tmp_path / "t", max_files=100
    )
    assert truncated is True
    assert meta["default_branch"] == "main"
    assert any("truncated=true" in n for n in notes)
    assert not (root / "evil").exists()
    assert (root / ".cursorrules").is_file()


def test_audit_github_labels_owner_repo_and_cleans_temp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from auctelis.export.reach_report import write_reach_report_artifacts

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    mcp = json.dumps(
        {"mcpServers": {"unpinned-demo": {"command": "npx", "args": ["-y", "demo-evil-mcp"]}}}
    )
    tree = {
        "truncated": False,
        "tree": [
            {"path": ".cursor/mcp.json", "type": "blob", "sha": "sha-mcp", "size": len(mcp)},
        ],
    }
    routes = {
        "https://api.github.com/repos/acme/app": {"default_branch": "main"},
        "https://api.github.com/repos/acme/app/git/trees/main": tree,
        "https://api.github.com/repos/acme/app/git/blobs/sha-mcp": {
            "encoding": "base64",
            "content": _b64(mcp),
            "size": len(mcp),
        },
    }
    _install_http(monkeypatch, routes)
    results, honesty = audit_github_repos(["acme/app"], max_repos=5, top=3)
    assert len(results) == 1
    assert results[0].repository == "acme/app"
    assert results[0].report is not None
    assert results[0].report["repository"] == "acme/app"
    assert "Temp" not in results[0].report["repository"]
    assert any("fetched" in n for n in honesty)
    out = tmp_path / "out"
    write_reach_report_artifacts(out, results[0].report, results[0].scan, cards=results[0].cards)
    md = (out / "reach-report.md").read_text(encoding="utf-8")
    assert "acme/app" in md


def test_rate_limit_is_fail_honest(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")

    def opener(req: Request, timeout: float = 0):
        raise HTTPError(
            req.full_url,
            429,
            "rate",
            hdrs={"X-RateLimit-Remaining": "0"},
            fp=None,
        )  # type: ignore[arg-type]

    monkeypatch.setattr("urllib.request.urlopen", opener)
    with pytest.raises(GitHubAuditError) as exc:
        resolve_targets(["acme"], max_repos=5)
    assert exc.value.status == 429
    assert exc.value.rate_limited is True


def test_github_web_base_derives_ghes_and_server_url(monkeypatch: pytest.MonkeyPatch):
    from auctelis import github_audit

    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    monkeypatch.setenv("GITHUB_API_URL", "https://git.corp.example/api/v3")
    assert github_audit._github_web_base() == "https://git.corp.example"
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://git.corp.example")
    assert github_audit._github_web_base() == "https://git.corp.example"
    monkeypatch.delenv("GITHUB_API_URL", raising=False)
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    assert github_audit._github_web_base() == "https://github.com"


def test_token_falls_back_to_gh_auth(monkeypatch: pytest.MonkeyPatch):
    from auctelis import github_audit

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    class _Proc:
        returncode = 0
        stdout = "gh-token-value\n"
        stderr = ""

    def fake_run(*args, **kwargs):
        assert args[0] == ["gh", "auth", "token"]
        assert kwargs.get("shell") is False
        return _Proc()

    monkeypatch.setattr(github_audit.subprocess, "run", fake_run)
    assert github_audit._token() == "gh-token-value"


def test_audit_rate_limit_skips_remaining(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    calls = {"n": 0}

    def opener(req: Request, timeout: float = 0):
        calls["n"] += 1
        url = req.full_url
        if "/repos/acme/one" in url and "/git/" not in url:
            raise HTTPError(
                url,
                429,
                "rate",
                hdrs={"X-RateLimit-Remaining": "0"},
                fp=None,
            )  # type: ignore[arg-type]
        raise HTTPError(url, 404, "not found", hdrs=None, fp=None)  # type: ignore[arg-type]

    monkeypatch.setattr("urllib.request.urlopen", opener)
    results, honesty = audit_github_repos(["acme/one", "acme/two"], max_repos=5)
    assert len(results) == 2
    assert all(r.skipped for r in results)
    assert any("rate limit" in n.lower() for n in honesty)
    # Second repo must not be fetched after rate-limit abort.
    assert not any(
        "acme/two" in (r.notes[0] if r.notes else "") and "404" in (r.notes[0] if r.notes else "")
        for r in results
    )
    assert results[1].notes and "rate limit" in results[1].notes[0].lower()


def test_audit_sets_default_branch_and_web_base(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    mcp = json.dumps({"mcpServers": {}})
    tree = {
        "truncated": False,
        "tree": [
            {"path": ".cursor/mcp.json", "type": "blob", "sha": "sha-mcp", "size": len(mcp)},
        ],
    }
    routes = {
        "https://api.github.com/repos/acme/app": {"default_branch": "develop"},
        "https://api.github.com/repos/acme/app/git/trees/develop": tree,
        "https://api.github.com/repos/acme/app/git/blobs/sha-mcp": {
            "encoding": "base64",
            "content": _b64(mcp),
            "size": len(mcp),
        },
    }
    _install_http(monkeypatch, routes)
    results, _ = audit_github_repos(["acme/app"], max_repos=5, top=3)
    assert results[0].report is not None
    assert results[0].report["default_branch"] == "develop"
    assert results[0].report["github_web_base"] == "https://github.com"


def test_resolve_targets_skips_forks_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    page = [
        {"full_name": "acme/owned", "archived": False, "fork": False},
        {"full_name": "acme/forked", "archived": False, "fork": True},
        {"full_name": "acme/other", "archived": False, "fork": False},
    ]
    routes = {"https://api.github.com/orgs/acme/repos": (page, 200, {"Link": ""})}
    _install_http(monkeypatch, routes)
    assert resolve_targets(["acme"], max_repos=10) == ["acme/owned", "acme/other"]
    assert resolve_targets(["acme"], max_repos=10, include_forks=True) == [
        "acme/owned",
        "acme/forked",
        "acme/other",
    ]


def test_http_200_remaining_zero_keeps_payload_and_short_circuits_next(
    monkeypatch: pytest.MonkeyPatch,
):
    from auctelis import github_audit

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    github_audit._reset_rate_limit_state()
    calls = {"n": 0}

    def opener(req: Request, timeout: float = 0):
        calls["n"] += 1
        url = req.full_url
        if calls["n"] == 1:
            return _FakeResponse(
                {"full_name": "acme/one", "default_branch": "main"},
                status=200,
                headers={"X-RateLimit-Remaining": "0"},
            )
        raise AssertionError(f"unexpected second HTTP call: {url}")

    monkeypatch.setattr("urllib.request.urlopen", opener)
    data, status, hdrs = github_audit._request_json(
        "https://api.github.com/repos/acme/one", token="tok"
    )
    assert status == 200
    assert data["full_name"] == "acme/one"
    assert hdrs.get("x-ratelimit-remaining") == "0"
    with pytest.raises(GitHubAuditError) as exc:
        github_audit._request_json("https://api.github.com/repos/acme/two", token="tok")
    assert exc.value.rate_limited is True
    assert calls["n"] == 1


def test_stage_repo_detects_already_watching(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    mcp = json.dumps({"mcpServers": {}})
    tree = {
        "truncated": False,
        "tree": [
            {"path": ".cursor/mcp.json", "type": "blob", "sha": "sha-mcp", "size": len(mcp)},
            {
                "path": ".github/workflows/auctelis.yml",
                "type": "blob",
                "sha": "sha-wf",
                "size": 20,
            },
        ],
    }
    routes = {
        "https://api.github.com/repos/acme/app": {"default_branch": "main"},
        "https://api.github.com/repos/acme/app/git/trees/main": tree,
        "https://api.github.com/repos/acme/app/git/blobs/sha-mcp": {
            "encoding": "base64",
            "content": _b64(mcp),
            "size": len(mcp),
        },
    }
    _install_http(monkeypatch, routes)
    _root, _notes, _trunc, meta = stage_repo_watched_files(
        "acme/app", staging_dir=tmp_path / "s", max_files=100
    )
    assert meta["already_watching"] is True


def test_audit_sets_already_watching_on_report(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    from auctelis import github_audit

    github_audit._reset_rate_limit_state()
    mcp = json.dumps({"mcpServers": {}})
    tree = {
        "truncated": False,
        "tree": [
            {"path": ".cursor/mcp.json", "type": "blob", "sha": "sha-mcp", "size": len(mcp)},
            {
                "path": ".github/workflows/auctelis-gate.yml",
                "type": "blob",
                "sha": "sha-wf",
                "size": 10,
            },
        ],
    }
    routes = {
        "https://api.github.com/repos/acme/app": {"default_branch": "main"},
        "https://api.github.com/repos/acme/app/git/trees/main": tree,
        "https://api.github.com/repos/acme/app/git/blobs/sha-mcp": {
            "encoding": "base64",
            "content": _b64(mcp),
            "size": len(mcp),
        },
    }
    _install_http(monkeypatch, routes)
    results, _ = audit_github_repos(["acme/app"], max_repos=5, top=3)
    assert results[0].report is not None
    assert results[0].report["already_watching"] is True
