"""Emit CI annotations from authdiff findings (GitHub Actions workflow commands)."""

from __future__ import annotations

from typing import Any

from authdiff.security.gating import GATE_FINDING_CLASSES, is_gate_finding

_LEVEL = {
    "CRITICAL": "error",
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "warning",
    "INFORMATIONAL": "notice",
}


def _escape(value: str, *, extra: str = "") -> str:
    """Escape values for GitHub Actions workflow commands."""
    out = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    for ch in extra:
        out = out.replace(ch, f"%{ord(ch):02X}")
    return out


def _evidence_locations(doc: dict[str, Any], finding: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {
        e.get("evidence_id"): e for e in doc.get("evidence_registry") or [] if e.get("evidence_id")
    }
    locs: list[dict[str, Any]] = []
    for eid in finding.get("evidence_ids") or []:
        ev = by_id.get(eid) or {}
        path = ev.get("file_path") or ev.get("path_or_source")
        if not path:
            continue
        locs.append(
            {
                "file": str(path).replace("\\", "/"),
                "line": int(ev["line_start"]) if ev.get("line_start") else None,
                "end_line": int(ev["line_end"]) if ev.get("line_end") else None,
            }
        )
    return locs


def iter_annotation_targets(
    doc: dict[str, Any],
    *,
    classes: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Flatten findings into annotation payloads (one per evidence location).

    Uses the same gate predicate as CI fail-on: empty evidence_ids, NAME_MARKER,
    and suppressed findings are excluded even when the class looks gateable.
    """
    wanted = classes if classes is not None else GATE_FINDING_CLASSES
    out: list[dict[str, Any]] = []
    for finding in doc.get("findings") or []:
        fclass = str(finding.get("finding_class") or "")
        if fclass not in wanted:
            continue
        if not is_gate_finding(finding):
            continue
        severity = str(finding.get("severity") or "INFORMATIONAL")
        title = str(finding.get("title") or finding.get("finding_id") or "finding")
        fid = str(finding.get("finding_id") or "")
        rule = str(finding.get("rule_id") or "")
        action = str(finding.get("recommended_action") or "")
        desc = str(finding.get("description") or title)
        message = f"{fid} [{fclass}/{severity}] {title}"
        if action:
            message = f"{message} — {action}"
        elif desc and desc != title:
            message = f"{message} — {desc[:240]}"
        locs = _evidence_locations(doc, finding)
        if not locs:
            out.append(
                {
                    "level": _LEVEL.get(severity, "warning"),
                    "title": f"{fid} {rule}".strip(),
                    "message": message,
                    "file": None,
                    "line": None,
                    "end_line": None,
                }
            )
            continue
        for loc in locs:
            out.append(
                {
                    "level": _LEVEL.get(severity, "warning"),
                    "title": f"{fid} {rule}".strip(),
                    "message": message,
                    "file": loc["file"],
                    "line": loc["line"],
                    "end_line": loc["end_line"],
                }
            )
    return out


def render_github_annotations(doc: dict[str, Any]) -> str:
    """Return GitHub Actions workflow commands for PR file annotations."""
    lines: list[str] = []
    for item in iter_annotation_targets(doc):
        level = item["level"]
        params: list[str] = []
        if item.get("file"):
            params.append(f"file={_escape(str(item['file']), extra=':,')}")
        if item.get("line"):
            params.append(f"line={item['line']}")
        if item.get("end_line") and item["end_line"] != item.get("line"):
            params.append(f"endLine={item['end_line']}")
        if item.get("title"):
            params.append(f"title={_escape(str(item['title']), extra=':,')}")
        prefix = f"::{level} {','.join(params)}::" if params else f"::{level}::"
        lines.append(prefix + _escape(str(item["message"])))
    return "\n".join(lines) + ("\n" if lines else "")


def render_text_annotations(doc: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in iter_annotation_targets(doc):
        loc = item.get("file") or "(no file)"
        if item.get("line"):
            loc = f"{loc}:{item['line']}"
        lines.append(f"[{item['level']}] {loc}  {item['message']}")
    return "\n".join(lines) + ("\n" if lines else "")
