"""Ruleset / branch-protection probe: OK vs MISSING vs UNVERIFIED."""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from auctelis.gate import _api_get_json, check_code_owner_ruleset


class _Response:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _install_routes(monkeypatch: pytest.MonkeyPatch, routes: dict[str, Any]) -> None:
    """Route by path suffix; value is a payload, an int status, or an exception."""

    def fake_urlopen(req, timeout: float = 0):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        for suffix, answer in routes.items():
            if url.endswith(suffix):
                if isinstance(answer, Exception):
                    raise answer
                if isinstance(answer, int):
                    raise urllib.error.HTTPError(url, answer, "error", None, None)
                return _Response(answer)
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


def _probe() -> tuple[str, str]:
    return check_code_owner_ruleset(
        repository="o/r",
        token="t",
        api_base="https://api.github.com",
        default_branch="main",
    )


def test_effective_rule_requiring_code_owner_review_is_ok(monkeypatch):
    _install_routes(
        monkeypatch,
        {
            "/repos/o/r/rules/branches/main": [
                {
                    "type": "pull_request",
                    "parameters": {"require_code_owner_review": True},
                }
            ]
        },
    )
    status, detail = _probe()
    assert status == "OK"
    assert "effective rules on main" in detail


def test_effective_rule_403_is_unverified(monkeypatch):
    _install_routes(monkeypatch, {"/repos/o/r/rules/branches/main": 403})
    status, detail = _probe()
    assert status == "UNVERIFIED"
    assert "HTTP 403" in detail


def test_disabled_ruleset_is_not_protection_and_classic_404_is_missing(monkeypatch):
    _install_routes(
        monkeypatch,
        {
            "/repos/o/r/rules/branches/main": [],
            "/repos/o/r/rulesets": [{"id": 7, "enforcement": "disabled"}],
            "/repos/o/r/branches/main/protection": 404,
        },
    )
    status, detail = _probe()
    assert status == "MISSING"
    assert "no branch protection" in detail


def test_ruleset_detail_fetch_is_used_when_list_has_no_inline_rules(monkeypatch):
    _install_routes(
        monkeypatch,
        {
            "/repos/o/r/rules/branches/main": [],
            "/repos/o/r/rulesets": [{"id": 7, "name": "protect", "enforcement": "active"}],
            "/repos/o/r/rulesets/7": {
                "id": 7,
                "enforcement": "active",
                "rules": [
                    {
                        "type": "pull_request",
                        "parameters": {"require_code_owner_review": True},
                    }
                ],
            },
        },
    )
    status, detail = _probe()
    assert status == "OK"
    assert "ruleset protect" in detail


def test_classic_protection_without_code_owner_reviews_is_missing(monkeypatch):
    _install_routes(
        monkeypatch,
        {
            "/repos/o/r/rules/branches/main": [],
            "/repos/o/r/rulesets": [],
            "/repos/o/r/branches/main/protection": {
                "required_pull_request_reviews": {"require_code_owner_reviews": False}
            },
        },
    )
    status, detail = _probe()
    assert status == "MISSING"
    assert "lacks require_code_owner_reviews" in detail


def test_network_error_is_unverified(monkeypatch):
    _install_routes(
        monkeypatch,
        {
            "/repos/o/r/rules/branches/main": urllib.error.URLError("offline"),
            "/repos/o/r/rulesets": urllib.error.URLError("offline"),
            "/repos/o/r/branches/main/protection": urllib.error.URLError("offline"),
        },
    )
    status, detail = _probe()
    assert status == "UNVERIFIED"
    assert "could not confirm" in detail


def test_api_get_json_rejects_non_http_scheme():
    assert _api_get_json("file:///etc/passwd", token="t") == (None, 0)
