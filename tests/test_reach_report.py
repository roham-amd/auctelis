"""AUCT-005 — shareable Agent Reach Report artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auctelis.check import build_check_report
from auctelis.cli import main
from auctelis.export.reach_report import (
    build_reach_report,
    diff_reach_reports,
    load_reach_baseline,
    render_reach_html,
    render_reach_md,
    write_reach_report_artifacts,
)
from auctelis.inventory.coverage import truncation_honesty_notes


def test_truncation_notes_from_synthetic_coverage():
    notes = truncation_honesty_notes(
        {
            "file_limit_reached_count": 1,
            "depth_limit_count": 2,
            "unparsed_agent_config_count": 3,
            "parser_events": [],
        }
    )
    assert any("File walk truncated" in n for n in notes)
    assert any("depth limit" in n for n in notes)
    assert any("NOT PARSED: 3" in n for n in notes)


def test_truncation_notes_from_parser_events_only():
    notes = truncation_honesty_notes(
        {
            "parser_events": [
                {"type": "file_limit_reached", "path": "."},
                {"type": "depth_limit", "path": "nested"},
            ]
        }
    )
    assert any("File walk truncated" in n for n in notes)
    assert any("depth limit" in n for n in notes)


def test_load_reach_baseline_rejects_non_object(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("[1, 2]\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="JSON object"):
        load_reach_baseline(path)


def test_html_escapes_script_in_record_name():
    doc = {
        "product_version": "0.13.0",
        "repository": "/tmp/repo",
        "honesty": {
            "disclaimer": "declared only",
            "coverage_line": "Coverage: ok",
            "truncation": [],
        },
        "reach": {
            "total": 1,
            "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
            "top": [
                {
                    "kind": "MCP Server Registration",
                    "name": "<script>alert(1)</script>",
                    "path": ".cursor/mcp.json",
                    "tier": 2,
                    "reason": "secrets",
                }
            ],
            "top_cards": [],
        },
        "cards": [],
        "pins": {},
    }
    html = render_reach_html(doc)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_demo_vulnerable_report_artifacts(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    demo = root / "examples" / "demo-vulnerable"
    report, cards, scan = build_check_report(demo, top=10)
    out = tmp_path / "out"
    doc = write_reach_report_artifacts(out, report, scan, cards=cards)
    assert (out / "reach-report.json").is_file()
    assert (out / "reach-report.md").is_file()
    assert (out / "reach-report.html").is_file()
    assert (out / "authority-sbom.json").is_file()
    md = (out / "reach-report.md").read_text(encoding="utf-8")
    assert "Agent Reach Report" in md
    assert "Honesty" in md
    assert doc["schema"] == "auctelis.reach_report.v1"
    # No writes outside out/
    assert all(p.resolve().is_relative_to(out.resolve()) for p in out.rglob("*") if p.is_file())


def test_baseline_diff_new_removed_changed():
    before = {
        "reach": {
            "tier_counts": {"tier0": 0, "tier1": 1, "tier2": 0},
            "top": [
                {
                    "kind": "MCP Server Registration",
                    "name": "a",
                    "path": "a.json",
                    "tier": 1,
                    "reason": "net",
                },
                {"kind": "Skill", "name": "keep", "path": "s.md", "tier": 0, "reason": "doc"},
            ],
        }
    }
    after = {
        "reach": {
            "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
            "top": [
                {
                    "kind": "MCP Server Registration",
                    "name": "b",
                    "path": "b.json",
                    "tier": 2,
                    "reason": "secrets",
                },
                {"kind": "Skill", "name": "keep", "path": "s.md", "tier": 1, "reason": "net"},
            ],
        }
    }
    diff = diff_reach_reports(before, after)
    assert len(diff["added"]) == 1 and diff["added"][0]["name"] == "b"
    assert len(diff["removed"]) == 1 and diff["removed"][0]["name"] == "a"
    assert len(diff["changed"]) == 1 and diff["changed"][0]["before"]["name"] == "keep"


def test_check_report_flag_cli(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    demo = root / "examples" / "demo-vulnerable"
    out = tmp_path / "report"
    code = main(["check", str(demo), "--report", str(out), "--top", "3"])
    assert code in {0, 1}
    assert (out / "reach-report.html").is_file()
    data = json.loads((out / "reach-report.json").read_text(encoding="utf-8"))
    assert data["reach"]["total"] >= 1


def test_build_reach_report_md_golden_shape():
    doc = build_reach_report(
        {
            "repository": "/repo",
            "coverage_line": "Coverage: SUPPORTED 1",
            "unparsed": 0,
            "reach": {
                "total": 1,
                "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                "top": [
                    {
                        "kind": "Hook",
                        "name": "curl-pipe",
                        "path": ".cursor/hooks.json",
                        "tier": 2,
                        "reason": "execute",
                    }
                ],
                "top_cards": ['+ hook "curl-pipe"'],
            },
            "pins": {},
            "counts": {},
            "delta": {},
            "label": "NONE",
            "verdict": "BASELINE_NEEDED",
            "schema_version": "authority-diff/1",
            "lock_path": "/repo/AUTHORITY.lock",
            "lock_present": False,
            "first_run": True,
            "meaningful": False,
        },
        None,
        cards=['+ hook "curl-pipe"'],
    )
    md = render_reach_md(doc)
    assert "curl-pipe" in md
    assert ".cursor/hooks.json" in md
    assert "DECLARED/CONFIGURED" in md or "declared" in md.lower()
