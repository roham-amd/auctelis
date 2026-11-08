"""Artifact-level vet for npm / PyPI packages (90-day path).

Inspects install scripts and declared provenance *without* executing the
package. Complements git-URL ``vet`` which only sees repo trees.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_NPM_NAME = re.compile(r"^(@[\w.-]+/)?[\w.-]+$")
_PYPI_NAME = re.compile(r"^[\w.-]+$")
_SCRIPT_RISK = re.compile(
    r"(curl\s+|wget\s+|iwr\s+|invoke-webrequest|powershell\s+-|cmd\s+/c|"
    r"chmod\s+\+x|/dev/tcp|base64\s+-d|eval\s*\(|\$\()",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ArtifactFinding:
    code: str
    severity: str
    summary: str
    evidence: str = ""


@dataclass(slots=True)
class ArtifactReport:
    ecosystem: str
    name: str
    version: str | None
    verdict: str
    findings: list[ArtifactFinding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem": self.ecosystem,
            "name": self.name,
            "version": self.version,
            "verdict": self.verdict,
            "findings": [
                {
                    "code": f.code,
                    "severity": f.severity,
                    "summary": f.summary,
                    "evidence": f.evidence,
                }
                for f in self.findings
            ],
            "metadata": self.metadata,
            "limitations": [
                "Does not execute install scripts or the package entrypoint.",
                "Registry metadata can change after this snapshot.",
                "Not a substitute for sandboxed tools/list (see authdiff snapshot).",
            ],
        }


def _http_json(url: str, *, timeout: float = 20.0) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "authdiff-artifact-vet/0.9"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object from {url}")
    return data


def _verdict(findings: list[ArtifactFinding]) -> str:
    if any(f.severity == "CRITICAL" for f in findings):
        return "REJECT"
    if any(f.severity in {"HIGH", "MEDIUM"} for f in findings):
        return "REVIEW"
    return "ALLOW_WITH_GAPS"


def vet_npm(name: str, *, version: str | None = None) -> ArtifactReport:
    if not _NPM_NAME.match(name):
        raise ValueError(f"Invalid npm package name: {name!r}")
    enc = name.replace("/", "%2F")
    meta = _http_json(f"https://registry.npmjs.org/{enc}")
    ver = version or str(meta.get("dist-tags", {}).get("latest") or "")
    versions = meta.get("versions") or {}
    pkg = versions.get(ver) if ver else None
    findings: list[ArtifactFinding] = []
    if not isinstance(pkg, dict):
        findings.append(
            ArtifactFinding("NPM_VERSION_MISSING", "HIGH", f"Version {ver!r} not in registry")
        )
        return ArtifactReport("npm", name, ver or None, _verdict(findings), findings, meta)

    scripts = pkg.get("scripts") or {}
    if isinstance(scripts, dict):
        for key in ("preinstall", "install", "postinstall", "prepare", "prepublish"):
            body = scripts.get(key)
            if not body:
                continue
            sev = "CRITICAL" if _SCRIPT_RISK.search(str(body)) else "HIGH"
            findings.append(
                ArtifactFinding(
                    "NPM_INSTALL_SCRIPT",
                    sev,
                    f"Package declares `{key}` lifecycle script",
                    evidence=str(body)[:240],
                )
            )

    dist = pkg.get("dist") or {}
    if not dist.get("integrity") and not dist.get("shasum"):
        findings.append(
            ArtifactFinding("NPM_NO_INTEGRITY", "MEDIUM", "dist lacks integrity/shasum")
        )

    return ArtifactReport(
        "npm",
        name,
        ver,
        _verdict(findings),
        findings,
        {
            "description": pkg.get("description"),
            "dist": {k: dist.get(k) for k in ("tarball", "integrity", "shasum") if dist.get(k)},
            "has_publishConfig": bool(pkg.get("publishConfig")),
        },
    )


def vet_pypi(name: str, *, version: str | None = None) -> ArtifactReport:
    if not _PYPI_NAME.match(name):
        raise ValueError(f"Invalid PyPI package name: {name!r}")
    meta = _http_json(f"https://pypi.org/pypi/{name}/json")
    info = meta.get("info") or {}
    ver = version or str(info.get("version") or "")
    findings: list[ArtifactFinding] = []
    requires = info.get("requires_dist") or []
    # setup.py / legacy sdist without pyproject is a rug-pull surface for build hooks.
    urls = meta.get("urls") or []
    has_wheel = any(u.get("packagetype") == "bdist_wheel" for u in urls if isinstance(u, dict))
    has_sdist = any(u.get("packagetype") == "sdist" for u in urls if isinstance(u, dict))
    if has_sdist and not has_wheel:
        findings.append(
            ArtifactFinding(
                "PYPI_SDIST_ONLY",
                "MEDIUM",
                "Only sdist published — build backends run on install",
            )
        )
    project_urls = info.get("project_urls") or {}
    if not project_urls and not info.get("home_page"):
        findings.append(
            ArtifactFinding("PYPI_NO_HOME", "LOW", "No project URL / home page declared")
        )
    yanked = False
    for u in urls:
        if isinstance(u, dict) and u.get("yanked"):
            yanked = True
            break
    if yanked:
        findings.append(ArtifactFinding("PYPI_YANKED_FILE", "HIGH", "At least one file is yanked"))

    return ArtifactReport(
        "pypi",
        name,
        ver,
        _verdict(findings),
        findings,
        {
            "summary": info.get("summary"),
            "requires_dist_count": len(requires) if isinstance(requires, list) else 0,
            "has_wheel": has_wheel,
            "has_sdist": has_sdist,
        },
    )


def parse_artifact_spec(spec: str) -> tuple[str, str, str | None]:
    """Parse ``npm:name[@ver]`` / ``pypi:name[==ver]`` / bare heuristics."""
    raw = spec.strip()
    if raw.startswith("npm:"):
        body = raw[4:]
        if "@" in body[1:]:  # allow scoped @scope/pkg@version
            name, _, ver = body.rpartition("@")
            return "npm", name, ver or None
        return "npm", body, None
    if raw.startswith("pypi:"):
        body = raw[5:]
        if "==" in body:
            name, _, ver = body.partition("==")
            return "pypi", name, ver or None
        return "pypi", body, None
    if raw.startswith("@") or "/" in raw:
        return "npm", raw, None
    return "pypi", raw, None


def run_artifact_vet(spec: str) -> ArtifactReport:
    eco, name, ver = parse_artifact_spec(spec)
    if eco == "npm":
        return vet_npm(name, version=ver)
    return vet_pypi(name, version=ver)


def write_artifact_report(report: ArtifactReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
