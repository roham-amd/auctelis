"""AUCT-048 — rollout funnel ledger (`--status`)."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from pathlib import Path

from auctelis.cli import main


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


def test_status_apply_mutual_exclusion(tmp_path: Path, capsys):
    path = _write(tmp_path, _fleet([_repo()]))
    code = main(["rollout", str(path), "--status", "--apply"])
    captured = capsys.readouterr()
    assert code == 2
    assert "mutually exclusive" in (captured.out + captured.err).lower()


def test_status_classifies_each_state(monkeypatch, capsys, tmp_path: Path):
    states = {
        "acme/watching": "watching_on_default",
        "acme/open": "open",
        "acme/merged": "merged",
        "acme/closed": "closed_unmerged",
        "acme/never": "never_opened",
        "acme/gone": "unknown",
    }

    def handler(method, url, data, _calls):
        assert method == "GET"
        path = _path(url)
        slug = None
        for name in states:
            owner, repo = name.split("/")
            if f"/repos/{owner}/{repo}" in path:
                slug = name
                break
        assert slug is not None
        if path == f"/repos/{slug}":
            if slug == "acme/gone":
                return 404, {"message": "Not Found"}
            return 200, {"default_branch": "main"}
        if path.endswith("/contents/.github/workflows"):
            if slug == "acme/watching":
                return 200, [{"name": "auctelis.yml"}]
            return 404, {"message": "Not Found"}
        if path.endswith("/pulls"):
            if slug == "acme/open":
                return 200, [
                    {
                        "state": "open",
                        "html_url": "https://github.com/acme/open/pull/1",
                        "number": 1,
                    }
                ]
            if slug == "acme/merged":
                return 200, [
                    {
                        "state": "closed",
                        "merged_at": "2026-01-01T00:00:00Z",
                        "html_url": "https://github.com/acme/merged/pull/2",
                        "number": 2,
                    }
                ]
            if slug == "acme/closed":
                return 200, [
                    {
                        "state": "closed",
                        "merged_at": None,
                        "html_url": "https://github.com/acme/closed/pull/3",
                        "number": 3,
                    }
                ]
            return 200, []
        raise AssertionError(f"unexpected {method} {url}")

    calls = _install(monkeypatch, handler)
    repos = [_repo(repository=slug, already_watching=(slug == "acme/watching")) for slug in states]
    path = _write(tmp_path, _fleet(repos))
    assert main(["rollout", str(path), "--status", "--json", "--max-prs", "10"]) == 0
    assert _writes(calls) == []
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] is True
    by_repo = {row["repository"]: row for row in payload["results"]}
    for slug, expected in states.items():
        assert by_repo[slug]["state"] == expected
    assert set(by_repo["acme/open"]) == {
        "repository",
        "state",
        "watching",
        "pr_url",
        "pr_number",
        "detail",
    }


def test_status_csv_header_subset_of_pilot_metrics(monkeypatch, capsys, tmp_path: Path):
    def handler(method, url, data, _calls):
        assert method == "GET"
        path = _path(url)
        if path == "/repos/acme/hot":
            return 200, {"default_branch": "main"}
        if path.endswith("/contents/.github/workflows"):
            return 404, {"message": "Not Found"}
        if path.endswith("/pulls"):
            return 200, []
        raise AssertionError(url)

    _install(monkeypatch, handler)
    path = _write(tmp_path, _fleet([_repo()]))
    assert main(["rollout", str(path), "--status", "--csv"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    header = out[0].split(",")
    pilot = (
        (Path(__file__).resolve().parents[1] / "eval" / "pilot-metrics.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
        .split(",")
    )
    assert set(header) <= set(pilot)


def test_status_allowed_under_agent_env(monkeypatch, capsys, tmp_path: Path):
    def handler(method, url, data, _calls):
        assert method == "GET"
        path = _path(url)
        if path == "/repos/acme/hot":
            return 200, {"default_branch": "main"}
        if path.endswith("/contents/.github/workflows"):
            return 200, [{"name": "auctelis.yml"}]
        if path.endswith("/pulls"):
            return 200, []
        raise AssertionError(url)

    _install(monkeypatch, handler)
    monkeypatch.setenv("AUCTELIS_AGENT", "1")
    path = _write(tmp_path, _fleet([_repo(already_watching=True)]))
    assert main(["rollout", str(path), "--status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["results"][0]["state"] == "watching_on_default"


def test_rollout_prefers_resolved_pin_snippet(monkeypatch, capsys, tmp_path: Path):
    seen: dict[str, str] = {}

    def handler(method, url, data, _calls):
        path = _path(url)
        if method == "GET" and path == "/repos/acme/hot":
            return 200, {"default_branch": "main"}
        if method == "GET" and path.endswith("/contents/.github/workflows"):
            return 404, {"message": "Not Found"}
        if method == "GET" and path.endswith("/pulls"):
            return 200, []
        if method == "GET" and "/git/ref/heads/" in path:
            return 200, {"object": {"sha": "abc"}}
        if method == "GET" and path.endswith("/auctelis.yml"):
            return 404, {"message": "Not Found"}
        if method == "POST" and path.endswith("/git/refs"):
            return 201, {}
        if method == "PUT":
            return 201, {}
        if method == "POST" and path.endswith("/pulls"):
            body = json.loads(data.decode())
            seen["body"] = body["body"]
            return 201, {"html_url": "https://github.com/acme/hot/pull/9"}
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
                                "resolved_config_snippet": ('"args": ["-y", "@linear/mcp@1.2.3"]'),
                                "resolved_at": "2026-11-22",
                            }
                        ],
                    },
                )
            ]
        ),
    )
    assert main(["rollout", str(path), "--apply"]) == 0
    body = seen["body"]
    assert "@linear/mcp@1.2.3" in body
    assert "trust-on-first-use: latest on 2026-11-22" in body
