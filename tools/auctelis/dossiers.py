"""IssueOps helpers and public Trust Dossier index generation."""

from __future__ import annotations

from typing import Any

from auctelis.inspect_target import parse_inspect_target


def parse_issue_target(body: str) -> str:
    """Extract and validate the inspect target from an IssueOps issue body."""
    lines = str(body or "").splitlines()
    after_heading = False
    raw = ""
    for line in lines:
        if after_heading:
            text = line.strip()
            if text:
                raw = text
                break
        elif line.strip() == "### Target":
            after_heading = True
    if not raw:
        raise ValueError("missing ### Target value")
    raw = raw.strip().strip("`").strip()
    kind, target = parse_inspect_target(raw)
    if kind == "local_path":
        raise ValueError("IssueOps does not accept local paths")
    return target


def build_dossier_index(rows: list[dict[str, Any]]) -> str:
    """Emit the public dossiers Markdown index table."""
    lines = [
        "# Public Trust Dossiers",
        "",
        "| Component | Target | Verdict | Red Flags | Dossier |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {component} | {target} | {verdict} | {red_flags} | {dossier} |".format(
                component=row.get("component", ""),
                target=row.get("target", ""),
                verdict=row.get("verdict", ""),
                red_flags=row.get("red_flags", ""),
                dossier=row.get("dossier", ""),
            )
        )
    return "\n".join(lines) + "\n"
