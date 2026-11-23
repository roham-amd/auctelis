"""Trust Dossier Markdown and terminal text renderers."""

from __future__ import annotations

from typing import Any

from auctelis.textutil import escape_markdown_inline, sanitize_terminal_line


def _provenance_items(doc: dict[str, Any]) -> list[tuple[str, str]]:
    prov = doc.get("provenance") or {}
    if not isinstance(prov, dict):
        return []
    return [(str(k), str(v)) for k, v in prov.items()]


def _red_flag_lines(doc: dict[str, Any]) -> list[dict[str, str]]:
    flags = doc.get("red_flags") or []
    out: list[dict[str, str]] = []
    if not isinstance(flags, list):
        return out
    for flag in flags:
        if not isinstance(flag, dict):
            continue
        out.append(
            {
                "severity": str(flag.get("severity") or ""),
                "title": str(flag.get("title") or ""),
                "path": str(flag.get("path") or ""),
                "rule_id": str(flag.get("rule_id") or ""),
                "evidence": str(flag.get("evidence") or ""),
            }
        )
    return out


def _reach_items(doc: dict[str, Any]) -> list[str]:
    reach = doc.get("reach") or {}
    if not isinstance(reach, dict):
        return []
    lines: list[str] = []
    total = reach.get("total")
    if total is not None:
        lines.append(f"total: {total}")
    tiers = reach.get("tier_counts")
    if isinstance(tiers, dict):
        parts = [f"{k}={v}" for k, v in tiers.items()]
        if parts:
            lines.append("tiers: " + " · ".join(parts))
    for card in reach.get("top_cards") or []:
        lines.append(str(card))
    if not any(isinstance(x, str) and x.startswith("+") for x in lines):
        for rec in reach.get("records") or []:
            if not isinstance(rec, dict):
                continue
            lines.append(
                f"{rec.get('kind') or '?'} {rec.get('name') or '?'} "
                f"@ {rec.get('path') or '?'} · tier {rec.get('tier')} · {rec.get('reason') or ''}"
            )
    return lines


def _unverified_items(doc: dict[str, Any]) -> list[str]:
    items = doc.get("unverified") or []
    if not isinstance(items, list):
        return []
    return [str(x) for x in items]


def render_dossier_markdown(doc: dict[str, Any]) -> str:
    """Render a Trust Dossier as Markdown (escaped for unsafe inline text)."""
    target = escape_markdown_inline(doc.get("target") or "")
    verdict = escape_markdown_inline(doc.get("verdict") or "")
    lines: list[str] = [
        f"# Trust Dossier: {target}",
        f"Verdict: {verdict}",
        "",
        "## Provenance",
        "",
    ]
    for key, value in _provenance_items(doc):
        lines.append(f"- **{escape_markdown_inline(key)}:** {escape_markdown_inline(value)}")
    lines.extend(["", "## Red Flags", ""])
    flags = _red_flag_lines(doc)
    if not flags:
        lines.append("_None._")
    else:
        for flag in flags:
            title = escape_markdown_inline(flag["title"])
            sev = escape_markdown_inline(flag["severity"])
            path = escape_markdown_inline(flag["path"])
            rule = escape_markdown_inline(flag["rule_id"])
            evidence = escape_markdown_inline(flag["evidence"], max_len=300)
            where = f" (`{path}`)" if flag["path"] else ""
            lines.append(f"- **{sev}** {title}{where} — `{rule}`: {evidence}")
    lines.extend(["", "## Reach", ""])
    reach_lines = _reach_items(doc)
    if not reach_lines:
        lines.append("_No reach records._")
    else:
        for item in reach_lines:
            lines.append(f"- {escape_markdown_inline(item, max_len=300)}")
    lines.extend(["", "## Unverified", ""])
    for item in _unverified_items(doc):
        lines.append(f"- {escape_markdown_inline(item, max_len=300)}")
    return "\n".join(lines)


def render_dossier_text(doc: dict[str, Any]) -> str:
    """Render a Trust Dossier as plain terminal text."""
    target = sanitize_terminal_line(doc.get("target") or "")
    verdict = sanitize_terminal_line(doc.get("verdict") or "")
    lines: list[str] = [
        f"# Trust Dossier: {target}",
        f"Verdict: {verdict}",
        "",
        "## Provenance",
        "",
    ]
    for key, value in _provenance_items(doc):
        lines.append(sanitize_terminal_line(f"- {key}: {value}"))
    lines.extend(["", "## Red Flags", ""])
    flags = _red_flag_lines(doc)
    if not flags:
        lines.append(sanitize_terminal_line("(none)"))
    else:
        for flag in flags:
            where = f" @ {flag['path']}" if flag["path"] else ""
            lines.append(
                sanitize_terminal_line(
                    f"- [{flag['severity']}] {flag['title']}{where} "
                    f"({flag['rule_id']}): {flag['evidence']}"
                )
            )
    lines.extend(["", "## Reach", ""])
    reach_lines = _reach_items(doc)
    if not reach_lines:
        lines.append(sanitize_terminal_line("(no reach records)"))
    else:
        for item in reach_lines:
            lines.append(sanitize_terminal_line(f"- {item}"))
    lines.extend(["", "## Unverified", ""])
    for item in _unverified_items(doc):
        lines.append(sanitize_terminal_line(f"- {item}"))
    return "\n".join(sanitize_terminal_line(line) for line in lines)
