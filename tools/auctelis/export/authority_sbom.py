"""Agent Authority SBOM — machine-readable authority inventory export.

Not a software SBOM substitute and not a safety certificate. Captures
DECLARED/CONFIGURED authority observed by auctelis for a single revision.
"""

from __future__ import annotations

from typing import Any

from auctelis.inventory.coverage import AUTHORITY_LAYERS
from auctelis.security.engine import ScanResult
from auctelis.versioning import load_versions, package_version, product_version


def build_authority_sbom(scan: ScanResult) -> dict[str, Any]:
    """Build an authority SBOM document from a completed scan."""
    versions = load_versions()
    components: list[dict[str, Any]] = []
    for comp in scan.inventory.get("components") or []:
        cid = str(comp.get("component_id") or comp.get("name") or "unknown")
        caps = [c.to_dict() for c in scan.capabilities if c.component_id == cid]
        components.append(
            {
                "component_id": cid,
                "name": comp.get("name"),
                "type": comp.get("type"),
                "path": comp.get("repository_path"),
                "adapter": comp.get("adapter"),
                "adapter_maturity": comp.get("adapter_maturity"),
                "fingerprint": comp.get("fingerprint"),
                "content_digest": comp.get("content_digest"),
                "authority_layer": "CONFIGURED",
                "capabilities": caps,
                "destinations": list(comp.get("destinations") or []),
                "priority_hints": list(comp.get("priority_hints") or []),
            }
        )

    return {
        "schema": "auctelis.authority_sbom.v1",
        "product": "auctelis",
        "product_version": scan.product_version or product_version(),
        "package_version": scan.package_version or package_version(),
        "rule_pack": versions.get("rule_pack"),
        "repository": scan.repository_path,
        "audited_commit": scan.commit,
        "collected_at_utc": scan.collected_at_utc,
        "authority_layers": AUTHORITY_LAYERS,
        "disclaimer": (
            "This export describes DECLARED/CONFIGURED authority observed by a "
            "passive scan. It does not certify safety, prove EFFECTIVE permissions, "
            "or establish VERIFIED runtime behavior."
        ),
        "components": components,
        "coverage": scan.coverage,
        "limitations": [
            "Passive mode never executes target code.",
            "Unsupported and MANUAL_ONLY surfaces may be absent or incomplete.",
            "Publishers may under-declare capabilities relative to observed behavior.",
        ],
    }
