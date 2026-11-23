"""Classify inspect targets into auctelis.trust_dossier.v1 documents."""

from __future__ import annotations

import re
import shlex
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Literal

from auctelis.check import build_check_report
from auctelis.github_audit import stage_repo_inspect_files
from auctelis.security.artifact_vet import ArtifactFinding, run_artifact_vet
from auctelis.security.engine import ScanResult, run_security_scan
from auctelis.security.package_source import (
    extract_archive_text_files,
    fetch_package_archive,
    stage_archive_to_dir,
)
from auctelis.textutil import validated_http_url

DOSSIER_SCHEMA = "auctelis.trust_dossier.v1"
UNVERIFIED_BASELINE = (
    "Runtime execution behavior (passive inspection never executes target code)",
    "Live network egress and remote tool responses",
    "Effective host OS/sandbox permissions",
    "Cryptographic publisher signature verification",
)

_NPX_RE = re.compile(r"^(?:npx|bunx)\s+(.+)$")
_UVX_RE = re.compile(r"^(?:uvx|pipx)\s+(.+)$")
_GH_BLOB_RE = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/blob/([^/]+)/(.+)$"
)
_GH_REPO_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
_FETCH_MAX = 512_000
_FETCH_TIMEOUT_S = 10.0


def parse_inspect_target(raw: str) -> tuple[str, str]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("empty target")

    m = _NPX_RE.match(text)
    if m:
        tokens = [t for t in shlex.split(m.group(1)) if not t.startswith("-")]
        if not tokens:
            raise ValueError(f"unsupported target: {text!r}")
        return "artifact", f"npm:{tokens[0]}"

    m = _UVX_RE.match(text)
    if m:
        tokens = shlex.split(m.group(1))
        kept: list[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok == "--from":
                i += 2
                continue
            if tok.startswith("-"):
                i += 1
                continue
            kept.append(tok)
            i += 1
        if not kept:
            raise ValueError(f"unsupported target: {text!r}")
        return "artifact", f"pypi:{kept[0]}"

    if text.startswith("npm:") or text.startswith("pypi:"):
        return "artifact", text

    m = _GH_BLOB_RE.match(text)
    if m:
        return (
            "raw_url",
            f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}",
        )

    m = _GH_REPO_RE.match(text)
    if m:
        return "github_repo", m.group(1)

    if text.startswith("https://") or text.startswith("http://"):
        validated_http_url(text)
        return "raw_url", text

    path = Path(text).expanduser()
    if path.exists():
        return "local_path", str(path.resolve())

    raise ValueError(f"unsupported target: {text!r}")


def _fetch_raw_bytes(url: str) -> bytes:
    safe = validated_http_url(url, what="inspect raw URL")
    req = urllib.request.Request(
        safe,
        headers={"User-Agent": "auctelis-inspect-target"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT_S) as resp:  # nosec B310
        return bytes(resp.read(_FETCH_MAX))


def _red_flags_from_artifact(findings: list[ArtifactFinding]) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": f.code,
            "severity": f.severity,
            "title": f.summary,
            "path": "",
            "evidence": f.evidence,
        }
        for f in findings
    ]


def _red_flags_from_scan(scan: ScanResult) -> list[dict[str, Any]]:
    by_id = {e.evidence_id: e for e in scan.evidences}
    out: list[dict[str, Any]] = []
    for finding in scan.findings:
        if finding.finding_class == "SECURITY_FINDING" or (
            finding.finding_class == "EXPOSURE"
            and finding.severity
            in {
                "CRITICAL",
                "HIGH",
                "MEDIUM",
            }
        ):
            pass
        else:
            continue
        path = finding.entry_point or ""
        evidence = finding.description or ""
        if finding.evidence_ids:
            ev = by_id.get(finding.evidence_ids[0])
            if ev is not None:
                if ev.file_path:
                    path = ev.file_path
                if ev.summary:
                    evidence = ev.summary
        out.append(
            {
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "title": finding.title,
                "path": path,
                "evidence": evidence,
            }
        )
    return out


def _red_flags_from_unparsed(scan: ScanResult) -> list[dict[str, Any]]:
    events = (scan.coverage or {}).get("parser_events") or []
    out: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get("type") or "") != "unparsed_agent_config":
            continue
        out.append(
            {
                "rule_id": "AUCTELIS-UNPARSED",
                "severity": "HIGH",
                "title": str(event.get("message") or "Unparsed agent config"),
                "path": str(event.get("path") or ""),
                "evidence": str(event.get("message") or ""),
            }
        )
    return out


def _verdict_from_flags(red_flags: list[dict[str, Any]]) -> str:
    severities = {str(rf.get("severity") or "") for rf in red_flags}
    if "CRITICAL" in severities:
        return "REJECT"
    if severities & {"HIGH", "MEDIUM"}:
        return "REVIEW"
    return "UNVERIFIED_CLEAN"


def inspect_target(raw: str, *, offline: bool = False) -> dict[str, Any]:
    kind, target = parse_inspect_target(raw)
    if offline and kind != "local_path":
        raise ValueError("--offline only supports local paths")

    artifact_findings: list[ArtifactFinding] = []
    tmp: tempfile.TemporaryDirectory[str] | None = None
    staged_root: Path | None = None
    try:
        if kind == "local_path":
            path = Path(target)
            if path.is_file():
                tmp = tempfile.TemporaryDirectory(prefix="auctelis-inspect-")
                tree = Path(tmp.name)
                shutil.copy2(path, tree / path.name)
            else:
                tree = path
        elif kind == "raw_url":
            tmp = tempfile.TemporaryDirectory(prefix="auctelis-inspect-")
            tree = Path(tmp.name)
            body = _fetch_raw_bytes(target)
            name = (
                "SKILL.md"
                if target.split("?", 1)[0].rstrip("/").lower().endswith(".md")
                else "mcp.json"
            )
            (tree / name).write_bytes(body)
        elif kind == "github_repo":
            tree, _notes, _trunc, _meta = stage_repo_inspect_files(target)
            staged_root = tree
        elif kind == "artifact":
            report = run_artifact_vet(target)
            artifact_findings = list(report.findings)
            eco: Literal["npm", "pypi"] = "npm" if report.ecosystem == "npm" else "pypi"
            data, archive_kind = fetch_package_archive(eco, report.metadata)
            tmp = tempfile.TemporaryDirectory(prefix="auctelis-inspect-")
            tree = Path(tmp.name)
            if data is not None and archive_kind is not None:
                files = extract_archive_text_files(data, kind=archive_kind)
                stage_archive_to_dir(files, tree)
        else:
            raise ValueError(f"unsupported target: {raw!r}")

        scan = run_security_scan(tree, apply_rules=True)
        check_report, _cards, _scan = build_check_report(tree)

        red_flags: list[dict[str, Any]] = []
        red_flags.extend(_red_flags_from_artifact(artifact_findings))
        red_flags.extend(_red_flags_from_scan(scan))
        red_flags.extend(_red_flags_from_unparsed(scan))

        return {
            "schema": DOSSIER_SCHEMA,
            "target": target,
            "target_kind": kind,
            "verdict": _verdict_from_flags(red_flags),
            "provenance": scan.to_findings_doc()["provenance"],
            "red_flags": red_flags,
            "reach": check_report.get("reach") or {},
            "unverified": list(UNVERIFIED_BASELINE),
        }
    finally:
        if tmp is not None:
            tmp.cleanup()
        if staged_root is not None:
            shutil.rmtree(staged_root, ignore_errors=True)
