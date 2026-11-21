"""``policy.require_review`` class matching (security-critical, no I/O)."""

from __future__ import annotations

from auctelis.security.review_classes import (
    finding_matches_review_class,
    require_review_hits,
)


def _finding(**overrides):
    finding = {
        "finding_id": "F-001",
        "rule_id": "AUCTELIS-RULE-003",
        "finding_class": "EXPOSURE",
        "exposure": "REMOTE_ENDPOINT",
        "capabilities": [],
        "evidence_strength": "LITERAL_CONFIG",
        "evidence_ids": ["E-001"],
        "suppressed": False,
    }
    finding.update(overrides)
    return finding


def test_remote_endpoint_matches_by_rule_id():
    assert finding_matches_review_class(_finding(), "remote_mcp_endpoint")
    assert finding_matches_review_class(
        _finding(rule_id="AUCTELIS-RULE-013"), "remote_mcp_endpoint"
    )


def test_remote_endpoint_matches_by_exposure():
    assert finding_matches_review_class(
        _finding(rule_id="AUCTELIS-RULE-001", exposure="REMOTE_ENDPOINT"),
        "remote_mcp_endpoint",
    )


def test_privileged_hook_requires_security_finding_class():
    hook = _finding(rule_id="AUCTELIS-RULE-004", finding_class="SECURITY_FINDING")
    assert finding_matches_review_class(hook, "privileged_hook")
    inventory_only = _finding(rule_id="AUCTELIS-RULE-004", finding_class="CAPABILITY")
    assert not finding_matches_review_class(inventory_only, "privileged_hook")


def test_credential_capability_needs_exposure_or_security_class():
    exposure = _finding(
        rule_id="AUCTELIS-RULE-999",
        finding_class="EXPOSURE",
        capabilities=["access_secrets"],
    )
    assert finding_matches_review_class(exposure, "credential_access")
    inventory = {**exposure, "finding_class": "CAPABILITY"}
    assert not finding_matches_review_class(inventory, "credential_access")


def test_suppressed_and_name_marker_never_satisfy_review():
    assert not finding_matches_review_class(_finding(suppressed=True), "remote_mcp_endpoint")
    assert not finding_matches_review_class(
        _finding(evidence_strength="NAME_MARKER"), "remote_mcp_endpoint"
    )


def test_unknown_class_never_matches():
    assert not finding_matches_review_class(_finding(), "not_a_class")


def test_require_review_hits_dedupes_and_skips_empty_classes():
    findings = [
        _finding(finding_id="F-001"),
        _finding(finding_id="F-001"),  # duplicate row
        _finding(finding_id="F-002", rule_id="AUCTELIS-RULE-013"),
    ]
    hits = require_review_hits(findings, ["remote_mcp_endpoint"])
    assert {hit["finding_id"] for hit in hits} == {"F-001", "F-002"}
    assert require_review_hits(findings, []) == []
    assert require_review_hits(findings, None) == []
