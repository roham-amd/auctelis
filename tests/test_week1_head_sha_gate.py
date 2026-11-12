"""Lock-only gate helpers: growth labels, ruleset probe, adoption bootstrap."""

from __future__ import annotations

from authdiff.gate import check_code_owner_ruleset, growth_label


def test_growth_label_matrix():
    assert growth_label({"additions": 1}) == "GROWTH"
    assert growth_label({"expansions": 1}) == "GROWTH"
    assert growth_label({"replacements": 1}) == "GROWTH"
    assert growth_label({"policy_changed": True}) == "GROWTH"
    assert growth_label({"reductions": 2}) == "REDUCTION"
    assert growth_label({}) == "NONE"


def test_ruleset_unverified_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    status, detail = check_code_owner_ruleset()
    assert status == "UNVERIFIED"
    assert "TOKEN" in detail or "token" in detail.lower() or "REPOSITORY" in detail


def test_adoption_bootstrap_decision_matrix():
    """Mirror Action fail-step: locked PR without base lock."""

    def fail_closed(*, base_lock: bool, head_lock: bool) -> bool:
        if base_lock:
            return False
        return not head_lock

    assert fail_closed(base_lock=False, head_lock=True) is False
    assert fail_closed(base_lock=False, head_lock=False) is True
    assert fail_closed(base_lock=True, head_lock=True) is False
