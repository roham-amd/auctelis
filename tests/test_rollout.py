"""AUCT-044 — cross-platform idempotent ``auctelis rollout``."""

from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.parse
from pathlib import Path

from auctelis.cli import main
from auctelis.export.reach_report import (
    build_fleet_reach_report,
    org_reusable_caller_yaml,
    render_fleet_reach_html,
    render_fleet_reach_md,
)


class _Resp:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _repo(**overrides: object) -> dict:
    doc = {
        "repository": "acme/hot",
        "already_watching": False,
        "default_branch": "main",
        "reach": {"total": 1, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1}},
    }
    doc.update(overrides)
    return doc


def _fleet(repos: list[dict]) -> dict:
    return {
        "schema": "auctelis.fleet_reach_report.v1",
        "repositories": repos,
    }


def _write(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "reach-report.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _install(monkeypatch, handler):
    calls: list[tuple[str, str, bytes | None]] = []

    def urlopen(req, timeout=30):
        method = req.get_method()
        url = req.full_url
        data = req.data
        calls.append((method, url, data))
        status, payload = handler(method, url, data, calls)
        raw = b"" if payload is None else json.dumps(payload).encode()
        if status >= 400:
            raise urllib.error.HTTPError(url, status, "err", None, io.BytesIO(raw))
        return _Resp(status, raw)

    monkeypatch.setattr("auctelis.rollout.urllib.request.urlopen", urlopen)
    monkeypatch.setattr("auctelis.rollout._token", lambda: "test-token")
    return calls


def _path(url: str) -> str:
    return urllib.parse.urlparse(url).path


def _writes(calls: list[tuple[str, str, bytes | None]]) -> list[tuple[str, str]]:
    return [(method, url) for method, url, _data in calls if method not in {"GET", "HEAD"}]


def test_dry_run_makes_no_requests(monkeypatch, capsys, tmp_path: Path):
    calls = _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    path = _write(
        tmp_path,
        _fleet(
            [
                _repo(),
                _repo(repository="acme/other", reach={"tier_counts": {"tier2": 0, "tier1": 1}}),
                _repo(repository="not a slug"),
                _repo(repository="acme/watched", already_watching=True),
            ]
        ),
    )
    code = main(["rollout", str(path), "--json"])
    assert code == 0
    assert calls == []
    payload = json.loads(capsys.readouterr().out)
    assert payload["apply"] is False
    assert payload["mode"] == "lockless"
    assert payload["planned"] == ["acme/hot"]


def test_dry_run_caps_unwatched_tier2_and_prints_mode(monkeypatch, capsys, tmp_path: Path):
    _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    repos = [_repo(repository=f"acme/r{i}") for i in range(12)]
    path = _write(tmp_path, _fleet(repos))
    assert main(["rollout", str(path), "--max-prs", "10"]) == 0
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "mode=lockless" in out
    assert out.count("would open Watch PR") == 10
    assert "acme/r10" not in out
    assert main(["rollout", str(path), "--max-prs", "0"]) == 2


def test_single_repo_report_and_org_reusable_dry_run(monkeypatch, capsys, tmp_path: Path):
    _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    path = _write(
        tmp_path,
        {
            "schema": "auctelis.reach_report.v1",
            "repository": "acme/one",
            "already_watching": False,
            "reach": {"tier_counts": {"tier2": 1}},
        },
    )
    assert main(["rollout", str(path), "--org-reusable", "acme"]) == 0
    out = capsys.readouterr().out
    assert "acme/one" in out
    assert "mode=org-reusable:acme" in out
    caller = org_reusable_caller_yaml("acme")
    assert len(caller.splitlines()) == 6
    assert "acme/.github/.github/workflows/auctelis-org-reusable.yml@main" in caller


def test_apply_opens_pr_on_clean_repo(monkeypatch, capsys, tmp_path: Path):
    def handler(method, url, data, _calls):
        path = _path(url)
        if method == "GET" and path == "/repos/acme/hot":
            return 200, {"default_branch": "main"}
        if method == "GET" and path.endswith("/contents/.github/workflows"):
            return 404, {"message": "Not Found"}
        if method == "GET" and path.endswith("/pulls"):
            return 200, []
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return 200, {"object": {"sha": "abc123"}}
        if method == "GET" and path.endswith("/git/ref/heads/auctelis/watch-prs"):
            return 404, {"message": "Not Found"}
        if method == "POST" and path.endswith("/git/refs"):
            return 201, {"ref": "refs/heads/auctelis/watch-prs"}
        if method == "GET" and path.endswith("/auctelis.yml"):
            return 404, {"message": "Not Found"}
        if method == "PUT" and path.endswith("/auctelis.yml"):
            body = json.loads(data.decode())
            assert "sha" not in body
            decoded = base64.b64decode(body["content"]).decode()
            assert "roham-amd/auctelis@" in decoded
            return 201, {"content": {"sha": "new"}}
        if method == "POST" and path.endswith("/pulls"):
            return 201, {"html_url": "https://github.com/acme/hot/pull/9"}
        raise AssertionError(f"unexpected {method} {url}")

    calls = _install(monkeypatch, handler)
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--apply"]) == 0
    out = capsys.readouterr().out
    assert "https://github.com/acme/hot/pull/9" in out
    assert any(method == "POST" and url.endswith("/pulls") for method, url, _data in calls)
    assert any(method == "PUT" for method, _url, _data in calls)


def test_apply_skips_existing_workflow_and_open_pr(monkeypatch, capsys, tmp_path: Path):
    def handler(method, url, _data, _calls):
        path = _path(url)
        repo = "gate" if "/acme/gate/" in path or path.endswith("/acme/gate") else "open"
        if method == "GET" and path in {"/repos/acme/gate", "/repos/acme/open"}:
            return 200, {"default_branch": "main"}
        if method == "GET" and path.endswith("/contents/.github/workflows"):
            name = "auctelis-gate.yml" if repo == "gate" else "ci.yml"
            if repo == "gate":
                return 200, [{"name": name, "type": "file"}]
            return 404, {"message": "Not Found"}
        if method == "GET" and path.endswith("/pulls"):
            return 200, [{"html_url": "https://github.com/acme/open/pull/4"}]
        raise AssertionError(f"unexpected {method} {url}")

    calls = _install(monkeypatch, handler)
    path = _write(
        tmp_path,
        _fleet([_repo(repository="acme/gate"), _repo(repository="acme/open")]),
    )
    assert main(["rollout", str(path), "--apply"]) == 0
    out = capsys.readouterr().out
    assert "acme/gate" in out
    assert "already on the default branch" in out
    assert "https://github.com/acme/open/pull/4" in out
    assert _writes(calls) == []


def test_apply_retries_put_with_blob_sha(monkeypatch, capsys, tmp_path: Path):
    file_gets = {"n": 0}

    def handler(method, url, data, _calls):
        path = _path(url)
        if method == "GET" and path == "/repos/acme/hot":
            return 200, {"default_branch": "main"}
        if method == "GET" and path.endswith("/contents/.github/workflows"):
            return 404, {"message": "Not Found"}
        if method == "GET" and path.endswith("/pulls"):
            return 200, []
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return 200, {"object": {"sha": "abc123"}}
        if method == "GET" and path.endswith("/git/ref/heads/auctelis/watch-prs"):
            return 200, {"object": {"sha": "abc123"}}
        if method == "GET" and path.endswith("/auctelis.yml"):
            file_gets["n"] += 1
            if file_gets["n"] == 1:
                return 404, {"message": "Not Found"}
            return 200, {"sha": "blobsha"}
        if method == "PUT" and path.endswith("/auctelis.yml"):
            body = json.loads(data.decode())
            if file_gets["n"] == 1:
                assert "sha" not in body
                return 422, {"message": "sha wasn't supplied"}
            assert body["sha"] == "blobsha"
            return 201, {"content": {"sha": "blobsha"}}
        if method == "POST" and path.endswith("/pulls"):
            return 201, {"html_url": "https://github.com/acme/hot/pull/3"}
        raise AssertionError(f"unexpected {method} {url}")

    _install(monkeypatch, handler)
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--apply"]) == 0
    assert "https://github.com/acme/hot/pull/3" in capsys.readouterr().out
    assert file_gets["n"] == 2


def test_apply_surfaces_workflow_scope_hint(monkeypatch, capsys, tmp_path: Path):
    def handler(method, url, _data, _calls):
        path = _path(url)
        if method == "GET" and path.rstrip("/").endswith("/repos/acme/hot"):
            return 200, {"default_branch": "main"}
        if method == "GET" and path.endswith("/contents/.github/workflows"):
            return 404, {"message": "Not Found"}
        if method == "GET" and path.endswith("/pulls"):
            return 200, []
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return 200, {"object": {"sha": "abc123"}}
        if method == "GET" and path.endswith("/git/ref/heads/auctelis/watch-prs"):
            return 404, {"message": "Not Found"}
        if method == "POST" and path.endswith("/git/refs"):
            return 201, {}
        if method == "GET" and path.endswith("/auctelis.yml"):
            return 404, {"message": "Not Found"}
        if method == "PUT":
            return 403, {"message": "Resource not accessible by integration"}
        raise AssertionError(f"unexpected {method} {url}")

    calls = _install(monkeypatch, handler)
    monkeypatch.setenv("GITHUB_API_URL", "https://ghes.example/api/v3")
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--apply"]) == 1
    out = capsys.readouterr().out
    assert "gh auth refresh -s workflow" in out
    assert "HTTP 403" in out
    assert calls[0][1].startswith("https://ghes.example/api/v3/")


def test_apply_org_reusable_encodes_six_line_caller(monkeypatch, tmp_path: Path):
    seen: dict[str, str] = {}

    def handler(method, url, data, _calls):
        path = _path(url)
        if method == "GET" and path == "/repos/acme/hot":
            return 200, {"default_branch": "main"}
        if method == "GET" and path.endswith("/contents/.github/workflows"):
            return 404, {"message": "Not Found"}
        if method == "GET" and path.endswith("/pulls"):
            return 200, []
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return 200, {"object": {"sha": "abc123"}}
        if method == "GET" and path.endswith("/git/ref/heads/auctelis/watch-prs"):
            return 404, {"message": "Not Found"}
        if method == "POST" and path.endswith("/git/refs"):
            return 201, {}
        if method == "GET" and path.endswith("/auctelis.yml"):
            return 404, {"message": "Not Found"}
        if method == "PUT":
            body = json.loads(data.decode())
            seen["yaml"] = base64.b64decode(body["content"]).decode()
            return 201, {}
        if method == "POST" and path.endswith("/pulls"):
            return 201, {"html_url": "https://github.com/acme/hot/pull/1"}
        raise AssertionError(f"unexpected {method} {url}")

    calls = _install(monkeypatch, handler)
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--apply", "--org-reusable", "acme"]) == 0
    assert seen["yaml"] == org_reusable_caller_yaml("acme")
    assert len(seen["yaml"].splitlines()) == 6
    assert calls[0][1].startswith("https://api.github.com/")


def test_agent_refuses_apply(monkeypatch, capsys, tmp_path: Path):
    calls = _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setenv("AUCTELIS_AGENT", "1")
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--apply"]) == 2
    assert "refused" in capsys.readouterr().out
    assert calls == []
    monkeypatch.delenv("AUCTELIS_AGENT")
    assert main(["rollout", str(path)]) == 0


def test_apply_without_token_exits_2(monkeypatch, capsys, tmp_path: Path):
    calls = _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr("auctelis.rollout._token", lambda: None)
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--apply"]) == 2
    assert calls == []
    err = capsys.readouterr().err
    assert "GITHUB_TOKEN" in err


def test_fleet_summary_leads_with_rollout_command():
    doc = build_fleet_reach_report(
        [
            (
                {
                    "repository": "acme/hot",
                    "default_branch": "main",
                    "github_web_base": "https://github.com",
                    "already_watching": False,
                    "coverage_line": "",
                    "unparsed": 0,
                    "reach": {
                        "total": 1,
                        "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                        "records": [],
                        "top": [],
                        "top_cards": [],
                    },
                    "pins": {"total": 0, "unpinned": 0, "items": []},
                    "counts": {},
                    "delta": {},
                    "label": "NONE",
                    "verdict": "BASELINE_NEEDED",
                    "schema_version": "authority-diff/1",
                    "lock_present": False,
                    "first_run": True,
                    "meaningful": False,
                },
                None,
                [],
            )
        ]
    )
    md = render_fleet_reach_md(doc)
    html = render_fleet_reach_html(doc)
    for text in (md, html):
        assert "rollout reach-report.json" in text
        assert text.index("rollout reach-report.json") < text.index("rollout-watch-prs.sh")
    summary = md.split("## Summary", 1)[1].split("##", 1)[0]
    assert "rollout reach-report.json --apply" in summary


def test_auct045_render_watch_pr_body_falls_back_when_reach_empty():
    from auctelis.rollout import _PR_BODY, render_watch_pr_body

    body = render_watch_pr_body(
        {
            "repository": "acme/empty",
            "reach": {"tier_counts": {"tier2": 1}, "records": [], "top": []},
        }
    )
    assert body == _PR_BODY


def test_auct045_select_targets_case_insensitive_repo_filter():
    from auctelis.rollout import select_targets

    doc = _fleet(
        [
            _repo(repository="acme/Hot"),
            _repo(repository="acme/other"),
        ]
    )
    matched = select_targets(doc, max_prs=10, repos=["ACME/hot"])
    assert [r["repository"] for r in matched] == ["acme/Hot"]


def test_auct045_repo_and_min_tier_filters(monkeypatch, capsys, tmp_path: Path):
    """AUCT-045: --repo selects named slugs; --min-tier 1 includes tier-1-only."""
    _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    path = _write(
        tmp_path,
        _fleet(
            [
                _repo(repository="acme/hot"),
                _repo(
                    repository="acme/tier1",
                    reach={"tier_counts": {"tier2": 0, "tier1": 1, "tier0": 0}},
                ),
                _repo(repository="acme/other"),
            ]
        ),
    )
    assert main(["rollout", str(path), "--repo", "ACME/hot", "--json"]) == 0
    planned = json.loads(capsys.readouterr().out)["planned"]
    assert planned == ["acme/hot"]

    assert main(["rollout", str(path), "--min-tier", "1", "--json"]) == 0
    planned = json.loads(capsys.readouterr().out)["planned"]
    assert planned == ["acme/hot", "acme/tier1", "acme/other"]


def test_auct045_inherits_org_reusable_from_report(monkeypatch, capsys, tmp_path: Path):
    _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    doc = _fleet([_repo()])
    doc["org_reusable"] = "acme"
    path = _write(tmp_path, doc)
    assert main(["rollout", str(path)]) == 0
    out = capsys.readouterr().out
    assert "mode=org-reusable:acme" in out


def test_auct045_pr_body_includes_findings_and_pin_fix(monkeypatch, tmp_path: Path):
    seen: dict[str, str] = {}

    def handler(method, url, data, _calls):
        path = _path(url)
        if method == "GET" and path == "/repos/acme/hot":
            return 200, {"default_branch": "main"}
        if method == "GET" and path.endswith("/contents/.github/workflows"):
            return 404, {"message": "Not Found"}
        if method == "GET" and path.endswith("/pulls"):
            return 200, []
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return 200, {"object": {"sha": "abc123"}}
        if method == "GET" and path.endswith("/git/ref/heads/auctelis/watch-prs"):
            return 404, {"message": "Not Found"}
        if method == "POST" and path.endswith("/git/refs"):
            return 201, {}
        if method == "GET" and path.endswith("/auctelis.yml"):
            return 404, {"message": "Not Found"}
        if method == "PUT":
            return 201, {}
        if method == "POST" and path.endswith("/pulls"):
            body = json.loads(data.decode())
            seen["body"] = body["body"]
            return 201, {"html_url": "https://github.com/acme/hot/pull/1"}
        raise AssertionError(f"unexpected {method} {url}")

    _install(monkeypatch, handler)
    path = _write(
        tmp_path,
        _fleet(
            [
                _repo(
                    reach={
                        "total": 1,
                        "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                        "records": [
                            {
                                "name": "linear",
                                "path": ".cursor/mcp.json",
                                "tier": 2,
                                "reason": "secrets",
                            }
                        ],
                    },
                    pins={
                        "total": 1,
                        "unpinned": 1,
                        "items": [
                            {
                                "name": "linear",
                                "path": ".cursor/mcp.json",
                                "config_snippet": ('"args": ["-y", "@linear/mcp@<exact-version>"]'),
                            }
                        ],
                    },
                )
            ]
        ),
    )
    assert main(["rollout", str(path), "--apply"]) == 0
    body = seen["body"]
    assert "linear" in body
    assert "**Pin fix:**" in body
    assert "@linear/mcp@<exact-version>" in body
    pin = next(line for line in body.splitlines() if "**Pin fix:**" in line)
    assert "\\[" not in pin
    assert len(body.splitlines()) <= 15


def test_auct045_fleet_summary_includes_org_reusable_cta():
    doc = build_fleet_reach_report(
        [
            (
                {
                    "repository": "acme/hot",
                    "default_branch": "main",
                    "github_web_base": "https://github.com",
                    "already_watching": False,
                    "coverage_line": "",
                    "unparsed": 0,
                    "reach": {
                        "total": 1,
                        "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                        "records": [],
                        "top": [],
                        "top_cards": [],
                    },
                    "pins": {"total": 0, "unpinned": 0, "items": []},
                    "counts": {},
                    "delta": {},
                    "label": "NONE",
                    "verdict": "BASELINE_NEEDED",
                    "schema_version": "authority-diff/1",
                    "lock_present": False,
                    "first_run": True,
                    "meaningful": False,
                },
                None,
                [],
            )
        ]
    )
    md = render_fleet_reach_md(doc, org_reusable="acme")
    html = render_fleet_reach_html(doc, org_reusable="acme")
    for text in (md, html):
        assert "--org-reusable acme" in text
        assert "rollout reach-report.json --org-reusable acme --apply" in text
        assert "#!/usr/bin/env bash" not in text
        assert "rollout-watch-prs.sh" in text


def _open_watch_pr(method: str, url: str, data: bytes | None, check_workflow) -> tuple[int, object]:
    path = _path(url)
    if method == "GET" and path == "/repos/acme/hot":
        return 200, {"default_branch": "main"}
    if method == "GET" and path.endswith("/contents/.github/workflows"):
        return 404, {"message": "Not Found"}
    if method == "GET" and path.endswith("/pulls"):
        return 200, []
    if method == "GET" and path.endswith("/git/ref/heads/main"):
        return 200, {"object": {"sha": "abc123"}}
    if method == "GET" and path.endswith("/git/ref/heads/auctelis/watch-prs"):
        return 404, {"message": "Not Found"}
    if method == "POST" and path.endswith("/git/refs"):
        return 201, {"ref": "refs/heads/auctelis/watch-prs"}
    if method == "GET" and path.endswith("/auctelis.yml"):
        return 404, {"message": "Not Found"}
    if method == "PUT" and path.endswith("/auctelis.yml"):
        body = json.loads((data or b"{}").decode())
        decoded = base64.b64decode(body["content"]).decode()
        check_workflow(decoded)
        return 201, {"content": {"sha": "new"}}
    if method == "POST" and path.endswith("/pulls"):
        return 201, {"html_url": "https://github.com/acme/hot/pull/9"}
    raise AssertionError(f"unexpected {method} {url}")


def test_auct052_show_body_text_and_json(monkeypatch, capsys, tmp_path: Path):
    calls = _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--show-body"]) == 0
    out = capsys.readouterr().out
    assert "would open Watch PR" in out
    assert "No AUTHORITY.lock required." in out
    assert calls == []

    assert main(["rollout", str(path), "--show-body", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["results"][0]["body"].startswith("Install Auctelis")
    assert "No AUTHORITY.lock required." in payload["results"][0]["body"]

    assert main(["rollout", str(path), "--json"]) == 0
    plain = json.loads(capsys.readouterr().out)
    assert "body" not in plain["results"][0]


def test_auct052_pin_sha_lightweight_and_annotated(monkeypatch, capsys, tmp_path: Path):
    from auctelis.versioning import product_version

    version = product_version()
    commit = "a" * 40
    annotated = "b" * 40
    path = _write(tmp_path, _fleet([_repo()]))

    def handler_for(kind: str):
        def handler(method, url, data, _calls):
            api = _path(url)
            if "/roham-amd/auctelis/git/" in api:
                if api.endswith(f"/git/ref/tags/v{version}"):
                    if kind == "lightweight":
                        return 200, {"object": {"type": "commit", "sha": commit}}
                    return 200, {"object": {"type": "tag", "sha": annotated}}
                if api.endswith(f"/git/tags/{annotated}"):
                    assert kind == "annotated"
                    return 200, {"object": {"type": "commit", "sha": commit}}
                raise AssertionError(api)

            def check(decoded: str) -> None:
                assert f"uses: roham-amd/auctelis@{commit} # v{version}" in decoded
                assert f"uses: roham-amd/auctelis@v{version}" not in decoded

            return _open_watch_pr(method, url, data, check)

        return handler

    for kind in ("lightweight", "annotated"):
        calls = _install(monkeypatch, handler_for(kind))
        assert main(["rollout", str(path), "--apply", "--pin-sha"]) == 0
        assert any("/git/ref/tags/" in url for _method, url, _data in calls)
        if kind == "lightweight":
            assert not any("/git/tags/" in url for _method, url, _data in calls)
        else:
            assert any(f"/git/tags/{annotated}" in url for _method, url, _data in calls)
        capsys.readouterr()


def test_auct052_pin_sha_api_failure_exits_2(monkeypatch, capsys, tmp_path: Path):
    def handler(method, url, _data, _calls):
        if method == "GET" and "/git/ref/tags/" in _path(url):
            return 404, {"message": "Not Found"}
        raise AssertionError(f"unexpected {method} {url}")

    _install(monkeypatch, handler)
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--pin-sha"]) == 2
    err = capsys.readouterr().err
    assert "--pin-sha" in err
    assert "org-reusable" in err


def test_auct052_pin_sha_org_reusable_is_noop(monkeypatch, capsys, tmp_path: Path):
    calls = _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--pin-sha", "--org-reusable", "acme"]) == 0
    assert calls == []
    capsys.readouterr()

    def handler(method, url, data, _calls):
        assert "/roham-amd/auctelis/" not in _path(url)

        def check(decoded: str) -> None:
            assert "auctelis-org-reusable.yml@main" in decoded
            assert "roham-amd/auctelis@" not in decoded

        return _open_watch_pr(method, url, data, check)

    calls = _install(monkeypatch, handler)
    assert main(["rollout", str(path), "--apply", "--pin-sha", "--org-reusable", "acme"]) == 0
    assert calls
    assert not any("/git/ref/tags/" in url for _method, url, _data in calls)


def test_auct052_pin_sha_with_status_exits_2(monkeypatch, capsys, tmp_path: Path):
    calls = _install(monkeypatch, lambda *_args: (_ for _ in ()).throw(AssertionError("network")))
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--pin-sha", "--status"]) == 2
    err = capsys.readouterr().err
    assert "--pin-sha" in err
    assert "--status" in err
    assert calls == []
