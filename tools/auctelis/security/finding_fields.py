"""Shared accessors for Finding objects and findings.json dict rows.

Gate, decision, PR comment, and require_review paths all need the same
dict-vs-dataclass field reads. Keep them here so severity/class/evidence
handling cannot drift between modules.
"""

from __future__ import annotations

from typing import Any


def finding_field(finding: Any, name: str, default: Any = None) -> Any:
    if isinstance(finding, dict):
        return finding.get(name, default)
    return getattr(finding, name, default)


def finding_str(finding: Any, name: str, default: str = "") -> str:
    value = finding_field(finding, name, default)
    return str(value or default)


def is_suppressed(finding: Any) -> bool:
    return bool(finding_field(finding, "suppressed", False))


def evidence_strength(finding: Any) -> str:
    return finding_str(finding, "evidence_strength")


def evidence_ids(finding: Any) -> list[str]:
    raw = (
        finding_field(finding, "evidence_ids", None)
        or finding_field(finding, "evidence", None)
        or []
    )
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item:
            out.append(item)
        elif isinstance(item, dict):
            eid = item.get("evidence_id") or item.get("id")
            if eid:
                out.append(str(eid))
    return out


def finding_class(finding: Any) -> str:
    return finding_str(finding, "finding_class")


def finding_severity(finding: Any) -> str:
    return finding_str(finding, "severity")
