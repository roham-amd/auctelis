"""Map ``policy.require_review`` authority classes to findings.

These classes name *what kind of authority* needs human acknowledgment.
Matching findings fail the gate even when severity alone would pass
``fail_on: high`` (e.g. MEDIUM remote MCP).
"""

from __future__ import annotations

from typing import Any

from auctelis.security.finding_fields import (
    evidence_strength,
    finding_field,
    finding_str,
    is_suppressed,
)

# Canonical class → matchers. Keep in sync with docs/POLICY.md examples.
REVIEW_CLASS_SPECS: dict[str, dict[str, frozenset[str]]] = {
    "remote_mcp_endpoint": {
        "rule_ids": frozenset({"AUCTELIS-RULE-003", "AUCTELIS-RULE-013"}),
        "exposures": frozenset({"REMOTE_ENDPOINT"}),
    },
    "privileged_hook": {
        "rule_ids": frozenset({"AUCTELIS-RULE-004"}),
        "finding_classes": frozenset({"SECURITY_FINDING"}),
    },
    "credential_access": {
        "rule_ids": frozenset({"AUCTELIS-RULE-006", "AUCTELIS-RULE-012"}),
        "capabilities": frozenset({"access_secrets"}),
    },
    "unattended_execution": {
        # RULE-007 alone is inventory for ordinary CI; gate on RULE-016
        # (privileged PR + agent) or capability matches that are already
        # SECURITY_FINDING / EXPOSURE (see finding_matches_review_class).
        "rule_ids": frozenset({"AUCTELIS-RULE-016"}),
        "capabilities": frozenset({"unattended_operation"}),
    },
}


def finding_matches_review_class(finding: Any, class_name: str) -> bool:
    """True when a non-suppressed finding matches a require_review class."""
    if is_suppressed(finding):
        return False
    # NAME_MARKER is triage-only — never satisfy require_review alone.
    if evidence_strength(finding) == "NAME_MARKER":
        return False
    spec = REVIEW_CLASS_SPECS.get(class_name)
    if not spec:
        return False
    rule_id = finding_str(finding, "rule_id")
    if rule_id in spec.get("rule_ids", frozenset()):
        required_classes = spec.get("finding_classes") or frozenset()
        fclass = finding_str(finding, "finding_class")
        return not required_classes or fclass in required_classes
    exposure = finding_str(finding, "exposure")
    if exposure in spec.get("exposures", frozenset()):
        return True
    caps = {str(c) for c in (finding_field(finding, "capabilities") or [])}
    if caps & spec.get("capabilities", frozenset()):
        # Capability-only match still requires a non-CAPABILITY finding class so
        # pure inventory observations do not auto-fail require_review.
        fclass = finding_str(finding, "finding_class")
        return fclass in {"EXPOSURE", "SECURITY_FINDING"}
    return False


def require_review_hits(
    findings: list[Any],
    classes: list[str] | None,
) -> list[dict[str, str]]:
    """Return ``{class, finding_id, rule_id}`` for each require_review hit."""
    if not classes:
        return []
    hits: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for class_name in classes:
        for finding in findings:
            if not finding_matches_review_class(finding, class_name):
                continue
            fid = finding_str(finding, "finding_id")
            key = (class_name, fid)
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                {
                    "class": class_name,
                    "finding_id": fid,
                    "rule_id": finding_str(finding, "rule_id"),
                }
            )
    return hits
