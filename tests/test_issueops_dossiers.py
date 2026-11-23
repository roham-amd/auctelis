"""AUCT-067: IssueOps parse helpers and public dossier index."""

from __future__ import annotations

from pathlib import Path

import pytest

from auctelis.dossiers import build_dossier_index, parse_issue_target

_REPO = Path(__file__).resolve().parents[1]


def test_parse_issue_target_extracts_npm_and_rejects_local_path() -> None:
    body = "### Target\n\n`npm:@modelcontextprotocol/server-filesystem`\n"
    assert parse_issue_target(body) == "npm:@modelcontextprotocol/server-filesystem"

    local_body = f"### Target\n\n`{_REPO}`\n"
    with pytest.raises(ValueError, match="IssueOps does not accept local paths"):
        parse_issue_target(local_body)


def test_issueops_workflow_blocks_inline_body_interpolation() -> None:
    text = (_REPO / ".github" / "workflows" / "issueops-inspect.yml").read_text(encoding="utf-8")
    assert "ISSUE_BODY: ${{ github.event.issue.body }}" in text
    run_blocks = []
    in_run = False
    for line in text.splitlines():
        if line.lstrip().startswith("run:"):
            in_run = True
            run_blocks.append(line)
            continue
        if in_run:
            if line.startswith(" ") or line.startswith("\t"):
                run_blocks.append(line)
            else:
                in_run = False
    joined = "\n".join(run_blocks)
    assert "${{ github.event.issue.body }}" not in joined


def test_build_dossier_index_renders_table() -> None:
    md = build_dossier_index(
        [
            {
                "component": "server-filesystem",
                "target": "npm:@modelcontextprotocol/server-filesystem",
                "verdict": "UNVERIFIED_CLEAN",
                "red_flags": 0,
                "dossier": "[server-filesystem.md](server-filesystem.md)",
            }
        ]
    )
    assert md.startswith("# Public Trust Dossiers")
    assert "| Component | Target | Verdict | Red Flags | Dossier |" in md
    assert "server-filesystem" in md
    assert "UNVERIFIED_CLEAN" in md
