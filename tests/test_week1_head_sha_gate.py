"""Lock-only gate helpers: growth labels, ruleset probe, adoption bootstrap."""

from __future__ import annotations

from authdiff.gate import adoption_bootstrap_verdict, check_code_owner_ruleset, growth_label


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
    assert adoption_bootstrap_verdict(base_lock_present=False, head_lock_present=True)["ok"]
    assert not adoption_bootstrap_verdict(base_lock_present=False, head_lock_present=False)["ok"]
    assert (
        adoption_bootstrap_verdict(base_lock_present=True, head_lock_present=True)["ceremony"]
        == "growth_gate"
    )
