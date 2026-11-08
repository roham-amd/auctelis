from __future__ import annotations

from typing import Any

from authdiff.versioning import product_version

_SARIF_SEVERITY = {
    "CRITICAL": "error",
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "note",
    "INFORMATIONAL": "note",
}


def findings_doc_to_sarif(
    doc: dict[str, Any],
    *,
    tool_version: str | None = None,
) -> dict[str, Any]:
    """Export authdiff findings.json (or audit report findings) to SARIF 2.1.0."""
    version = tool_version or str(doc.get("product_version") or product_version())
    evidence_by_id = {
        e["evidence_id"]: e for e in doc.get("evidence_registry") or [] if e.get("evidence_id")
    }
    # Compatibility with audit-report evidence shape.
    for e in doc.get("evidence_registry") or []:
        if e.get("evidence_id") and "path_or_source" in e and "file_path" not in e:
            evidence_by_id[e["evidence_id"]] = {
                **e,
                "file_path": e.get("path_or_source"),
            }

    rules: dict[str, dict] = {}
    results: list[dict] = []

    for finding in doc.get("findings") or []:
        fid = finding.get("finding_id", "UNKNOWN")
        rule_id = finding.get("rule_id") or f"authdiff/{fid}"
        rules[rule_id] = {
            "id": rule_id,
            "name": finding.get("title", fid),
            "shortDescription": {"text": finding.get("title", fid)},
        }
        locations: list[dict] = []
        for eid in finding.get("evidence_ids") or []:
            ev = evidence_by_id.get(eid)
            if not ev:
                continue
            path = ev.get("file_path") or ev.get("path_or_source")
            if not path:
                continue
            region: dict[str, int] = {}
            if ev.get("line_start"):
                region["startLine"] = int(ev["line_start"])
            if ev.get("line_end"):
                region["endLine"] = int(ev["line_end"])
            loc: dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {"uri": path},
                }
            }
            if region:
                loc["physicalLocation"]["region"] = region
            locations.append(loc)
        if not locations:
            # Still emit finding without location so CI can see rule hits.
            results.append(
                {
                    "ruleId": rule_id,
                    "level": _SARIF_SEVERITY.get(finding.get("severity", "INFORMATIONAL"), "note"),
                    "message": {"text": finding.get("description") or finding.get("title") or fid},
                }
            )
            continue
        results.append(
            {
                "ruleId": rule_id,
                "level": _SARIF_SEVERITY.get(finding.get("severity", "INFORMATIONAL"), "note"),
                "message": {"text": finding.get("description") or finding.get("title") or fid},
                "locations": locations,
            }
        )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "authdiff",
                        "version": version,
                        "informationUri": ("https://github.com/roham-amd/authdiff"),
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def report_to_sarif(
    report: dict[str, Any],
    *,
    tool_version: str | None = None,
) -> dict[str, Any]:
    return findings_doc_to_sarif(report, tool_version=tool_version)
