"""AUCT-002 — post once on first run, then stay quiet."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import write_authority_lock
from auctelis.cli import main
from auctelis.export.pr_comment import (
    AUCTELIS_COMMENT_MARKER,
    render_first_run_comment,
)
from auctelis.gate import run_gate


def _mcp(root: Path, servers: dict) -> None:
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": servers}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_gate_report_carries_head_reach_snapshot(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(
        root,
        {
            "linear": {
                "command": "npx",
                "args": ["-y", "@linear/mcp"],
                "env": {"API_TOKEN": "x"},
            }
        },
    )
    base, _lock = write_authority_lock(root)
    report, _code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    reach = report["reach"]
    assert reach["total"] >= 1
    assert reach["tier_counts"]["tier2"] >= 1
    assert reach["top_cards"]


def test_quiet_gate_writes_first_run_comment(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base, _lock = write_authority_lock(root)
    out = tmp_path / "out"
    monkeypatch.setenv("AUCTELIS_OUTPUT_DIR", str(out))

    code = main(
        [
            "gate",
            str(root),
            "--base-lock",
            str(base),
            "--skip-ruleset-check",
            "--comment-only",
        ]
    )
    assert code == 0
    # Quiet-on-NONE still applies: no normal diff comment.
    assert not (out / "pr-comment.md").exists()
    assert (out / "comment-skip.txt").is_file()

    first_run = out / "comment-first-run.md"
    assert first_run.is_file()
    body = first_run.read_text(encoding="utf-8")
    assert AUCTELIS_COMMENT_MARKER in body
    assert "first run" in body
    assert "**Watching:**" in body
    assert "`PASS`" in body
    assert "No authority change" not in body.replace("did not change", "")
    # ≤12 visible lines, marker excluded.
    assert len([line for line in body.splitlines() if line]) <= 12


def test_first_run_renderer_never_says_pass_on_growth():
    body = render_first_run_comment(
        {
            "verdict": "NEEDS_REVIEW",
            "label": "GROWTH",
            "meaningful_authority_change": True,
            "reach": {
                "total": 3,
                "tier_counts": {"tier0": 0, "tier1": 1, "tier2": 2},
                "top_cards": ['+ mcp "linear" → mcp.linear.app · tier 2 (secrets)'],
            },
            "delta": {
                "summary": {"additions": 1, "mcp_tools_added": 0},
                "records": {
                    "added": [
                        {
                            "kind": "MCP Server Registration",
                            "name": "linear",
                            "path": ".cursor/mcp.json",
                        }
                    ],
                    "changed": [],
                    "removed": [],
                },
            },
        }
    )
    assert "**Verdict:** `NEEDS_REVIEW`" in body
    assert "**Verdict:** `PASS`" not in body
    assert "linear" in body


def test_first_run_install_workflow_only_is_pass():
    body = render_first_run_comment(
        {
            "verdict": "NEEDS_REVIEW",
            "label": "GROWTH",
            "meaningful_authority_change": True,
            "unparsed": 0,
            "lock_tree_drift": False,
            "reach": {
                "total": 1,
                "tier_counts": {"tier0": 1, "tier1": 0, "tier2": 0},
                "top_cards": ['+ ci "auctelis"'],
            },
            "delta": {
                "summary": {
                    "additions": 1,
                    "mcp_tools_added": 0,
                    "mcp_tools_changed": 0,
                    "policy_changed": False,
                },
                "records": {
                    "added": [
                        {
                            "kind": "CI Workflow",
                            "name": "auctelis",
                            "path": ".github/workflows/auctelis.yml",
                        }
                    ],
                    "changed": [],
                    "removed": [],
                },
            },
        }
    )
    assert "**Verdict:** `PASS`" in body
    assert "**Watching:**" in body


def test_first_run_install_plus_mcp_shows_needs_review_and_card():
    body = render_first_run_comment(
        {
            "verdict": "NEEDS_REVIEW",
            "label": "GROWTH",
            "meaningful_authority_change": True,
            "unparsed": 0,
            "reach": {
                "total": 2,
                "tier_counts": {"tier0": 1, "tier1": 0, "tier2": 1},
                "top_cards": [
                    '+ mcp "smuggle" → tier 2 (secrets)',
                    '+ ci "auctelis"',
                ],
            },
            "delta": {
                "summary": {
                    "additions": 2,
                    "mcp_tools_added": 0,
                    "mcp_tools_changed": 0,
                    "policy_changed": False,
                },
                "records": {
                    "added": [
                        {
                            "kind": "CI Workflow",
                            "name": "auctelis",
                            "path": ".github/workflows/auctelis.yml",
                        },
                        {
                            "kind": "MCP Server Registration",
                            "name": "smuggle",
                            "path": ".cursor/mcp.json",
                            "env_keys": ["TOKEN"],
                            "capabilities": ["access_secrets"],
                            "evidence_strength": "LITERAL_CONFIG",
                        },
                    ],
                    "changed": [],
                    "removed": [],
                },
            },
        }
    )
    assert "**Verdict:** `NEEDS_REVIEW`" in body
    assert "smuggle" in body
    assert "**Watching:**" in body


def test_first_run_renderer_names_zero_reach_honestly():
    body = render_first_run_comment(
        {
            "verdict": "PASS",
            "label": "NONE",
            "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}, "top": []},
        }
    )
    assert "No agent configuration was discovered" in body


def test_action_posts_first_run_only_without_sticky():
    action = (
        Path(__file__).resolve().parents[1] / ".github" / "actions" / "auctelis-gate" / "action.yml"
    )
    text = action.read_text(encoding="utf-8")
    assert "comment-first-run.md" in text
    assert "FIRST_RUN" in text
    assert "existing_id" in text
    assert "workflow_added" in text
    assert ".github/workflows/auctelis*.yml" in text
    assert 'cp "$FIRST_RUN" "$COMMENT"' in text
    assert "prepending Watching banner" in text
    assert "auctelis-dev" not in text


def test_install_shaped_growth_still_writes_first_run(tmp_path: Path, monkeypatch):
    """Growth (e.g. new workflow CI record) must still emit comment-first-run.md."""
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base, _lock = write_authority_lock(root)
    # Add a second MCP → GROWTH vs sealed base.
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {
                "command": "npx",
                "args": ["-y", "@new/mcp"],
                "env": {"TOKEN": "x"},
            },
        },
    )
    out = tmp_path / "out"
    monkeypatch.setenv("AUCTELIS_OUTPUT_DIR", str(out))
    code = main(
        [
            "gate",
            str(root),
            "--base-lock",
            str(base),
            "--skip-ruleset-check",
            "--comment-only",
        ]
    )
    assert code == 0
    assert (out / "pr-comment.md").is_file()
    assert (out / "comment-first-run.md").is_file()
    assert "**Watching:**" in (out / "comment-first-run.md").read_text(encoding="utf-8")
