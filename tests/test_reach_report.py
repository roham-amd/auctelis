"""AUCT-005 — shareable Agent Reach Report artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auctelis.check import build_check_report, render_check
from auctelis.cli import main
from auctelis.export.reach_report import (
    build_reach_report,
    diff_reach_reports,
    load_reach_baseline,
    render_reach_html,
    render_reach_md,
    write_reach_report_artifacts,
)
from auctelis.inventory.coverage import (
    ADAPTER_COVERAGE,
    family_coverage_line_from_coverage,
    truncation_honesty_notes,
)


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
    with pytest.raises(ValueError, match="JSON object"):
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
                {
                    "kind": "Skill",
                    "name": "keep",
                    "path": "s.md",
                    "tier": 0,
                    "reason": "doc",
                },
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
                {
                    "kind": "Skill",
                    "name": "keep",
                    "path": "s.md",
                    "tier": 1,
                    "reason": "net",
                },
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


def test_report_includes_all_tier2_beyond_top_limit(tmp_path: Path):
    """AUCT-007: default --top 5 must not drop tier-2 rows from the HTML/MD report."""
    root = tmp_path / "repo"
    cfg = root / ".cursor"
    cfg.mkdir(parents=True)
    servers = {
        f"srv{i}": {
            "command": "npx",
            "args": ["-y", f"@demo/mcp-{i}"],
            "env": {f"TOKEN_{i}": "x"},
        }
        for i in range(8)
    }
    (cfg / "mcp.json").write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n")
    out = tmp_path / "out"
    code = main(["check", str(root), "--report", str(out)])
    assert code in {0, 1}
    data = json.loads((out / "reach-report.json").read_text(encoding="utf-8"))
    records = data["reach"]["records"]
    assert len(records) >= 8
    assert len(data["reach"]["top"]) == 5
    html = (out / "reach-report.html").read_text(encoding="utf-8")
    md = (out / "reach-report.md").read_text(encoding="utf-8")
    for i in range(8):
        assert f"srv{i}" in html
        assert f"srv{i}" in md

    before = {
        "reach": {
            "records": [
                {
                    "kind": "mcp",
                    "name": f"srv{i}",
                    "path": ".cursor/mcp.json",
                    "tier": 2,
                    "reason": "secrets",
                }
                for i in range(8)
            ],
            "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 8},
        }
    }
    after = {
        "reach": {
            "records": [
                *[
                    {
                        "kind": "mcp",
                        "name": f"srv{i}",
                        "path": ".cursor/mcp.json",
                        "tier": 2,
                        "reason": "secrets",
                    }
                    for i in range(6)
                ],
                {
                    "kind": "mcp",
                    "name": "srv6",
                    "path": ".cursor/mcp.json",
                    "tier": 2,
                    "reason": "execute",
                },
                {
                    "kind": "mcp",
                    "name": "srv7",
                    "path": ".cursor/mcp.json",
                    "tier": 2,
                    "reason": "secrets",
                },
            ],
            "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 8},
        }
    }
    diff = diff_reach_reports(before, after)
    assert any((c.get("before") or {}).get("name") == "srv6" for c in diff["changed"])


def test_coverage_line_names_uninspected_families_not_zero():
    """AUCT-015: a discovered MANUAL_ONLY 0 must not hide adapter-less families."""
    line = family_coverage_line_from_coverage(
        {
            "component_counts_by_maturity": {
                "SUPPORTED": 1,
                "PARTIAL": 4,
                "MANUAL_ONLY": 0,
                "UNSUPPORTED": 0,
            }
        }
    )
    manual = sum(1 for row in ADAPTER_COVERAGE if row["maturity"] == "MANUAL_ONLY")
    unsupported = sum(1 for row in ADAPTER_COVERAGE if row["maturity"] == "UNSUPPORTED")
    assert "discovered SUPPORTED 1 · PARTIAL 4" in line
    assert f"uninspected families: {manual} MANUAL_ONLY · {unsupported} UNSUPPORTED" in line
    assert "MANUAL_ONLY 0" not in line


def test_pins_line_pluralizes_on_total(tmp_path: Path):
    """AUCT-015: 1 of 2 MCP servers unpinned (not 'MCP server')."""
    root = tmp_path / "repo"
    cfg = root / ".cursor"
    cfg.mkdir(parents=True)
    (cfg / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "pinned": {"command": "npx", "args": ["-y", "@demo/pinned@1.2.3"]},
                    "floating": {"command": "npx", "args": ["-y", "@demo/floating"]},
                }
            }
        ),
        encoding="utf-8",
    )
    report, cards, _scan = build_check_report(root)
    text = render_check(report, cards)
    assert "1 of 2 MCP servers unpinned" in text


def _parity_doc() -> dict:
    return {
        "product_version": "0.15.0",
        "repository": "/repo",
        "honesty": {
            "disclaimer": "declared only",
            "coverage_line": "Coverage: discovered SUPPORTED 0 · PARTIAL 4",
            "truncation": [],
        },
        "coverage": {
            "manual_review_families": ["Browser agents", "Runtime behavior"],
        },
        "reach": {
            "total": 1,
            "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
            "top": [
                {
                    "kind": "MCP Server Registration",
                    "name": "linear",
                    "path": ".cursor/mcp.json",
                    "tier": 2,
                    "reason": "secrets",
                }
            ],
            "top_cards": [],
        },
        "cards": [],
        "pins": {
            "total": 1,
            "unpinned": 1,
            "items": [
                {
                    "name": "linear",
                    "path": ".cursor/mcp.json",
                    "pin_state": "floating",
                    "suggestion": "pin the package: npx -y @linear/mcp@<exact-version>",
                }
            ],
        },
    }


def test_html_report_parity_pins_and_manual_families():
    """AUCT-014: HTML carries the same pins / blind-spot sections as Markdown."""
    doc = _parity_doc()
    html = render_reach_html(doc)
    md = render_reach_md(doc)
    for text in (html, md):
        assert "Unpinned MCP launchers" in text
        assert "@linear/mcp" in text
        assert "Not auto-inspected" in text
        assert "Browser agents" in text
        assert "Runtime behavior" in text
        assert "init --lockless" in text
    # Suggestion text is present in both; HTML and Markdown escape angle brackets.
    assert "pin the package: npx -y @linear/mcp@&lt;exact-version&gt;" in html
    assert "pin the package: npx -y @linear/mcp@&lt;exact-version&gt;" in md


def test_fleet_check_ranks_repositories_by_tier2(tmp_path: Path):
    """AUCT-014: multi-path check --report writes one ranked fleet artifact."""
    top = tmp_path / "repo_top"
    cfg = top / ".cursor"
    cfg.mkdir(parents=True)
    (cfg / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "a": {
                        "command": "npx",
                        "args": ["-y", "@demo/a"],
                        "env": {"TOKEN_A": "x"},
                    },
                    "b": {
                        "command": "npx",
                        "args": ["-y", "@demo/b"],
                        "env": {"TOKEN_B": "x"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    other = tmp_path / "repo_other"
    other.mkdir()
    (other / "README.md").write_text("x\n", encoding="utf-8")
    out = tmp_path / "fleet"
    code = main(["check", str(other), str(top), "--report", str(out)])
    assert code in {0, 1}
    data = json.loads((out / "reach-report.json").read_text(encoding="utf-8"))
    assert data["schema"] == "auctelis.fleet_reach_report.v1"
    assert data["repository_count"] == 2
    assert data["totals"]["tier2"] == 2
    assert data["totals"]["unpinned"] == 2
    names = [Path(repo["repository"]).name for repo in data["repositories"]]
    assert names == ["repo_top", "repo_other"]
    html = (out / "reach-report.html").read_text(encoding="utf-8")
    md = (out / "reach-report.md").read_text(encoding="utf-8")
    for text in (html, md):
        assert "repo_top" in text
        assert "repo_other" in text
        assert "Unpinned MCP launchers" in text
        assert "Not auto-inspected" in text
        assert "init --lockless" in text


def test_fleet_check_requires_report(tmp_path: Path, capsys):
    first = tmp_path / "one"
    second = tmp_path / "two"
    for path in (first, second):
        path.mkdir()
        (path / "README.md").write_text("x\n", encoding="utf-8")
    code = main(["check", str(first), str(second)])
    assert code == 2
    assert "--report" in capsys.readouterr().out


def test_fleet_check_rejects_single_repo_flags(tmp_path: Path, capsys):
    first = tmp_path / "one"
    second = tmp_path / "two"
    for path in (first, second):
        path.mkdir()
        (path / "README.md").write_text("x\n", encoding="utf-8")
    out = tmp_path / "fleet"
    for flag, value in (
        ("--lock-file", tmp_path / "AUTHORITY.lock"),
        ("--baseline", tmp_path / "baseline.json"),
    ):
        code = main(["check", str(first), str(second), "--report", str(out), flag, str(value)])
        assert code == 2
        assert "single-repo" in capsys.readouterr().out
    code = main(["check", str(first), str(second), "--report", str(out), "--pins"])
    assert code == 2
    assert "--pins" in capsys.readouterr().out
    assert not out.exists()


def test_fleet_check_rejects_missing_directory(tmp_path: Path, capsys):
    first = tmp_path / "one"
    first.mkdir()
    missing = tmp_path / "does-not-exist"
    code = main(["check", str(first), str(missing), "--report", str(tmp_path / "fleet")])
    assert code == 2
    assert "not a directory" in capsys.readouterr().out


def test_report_json_stdout_stays_machine_readable(tmp_path: Path, capsys):
    """``--json --report`` keeps stdout pure JSON; the written-file note goes to stderr."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("x\n", encoding="utf-8")
    out = tmp_path / "out"
    code = main(["check", str(root), "--report", str(out), "--json"])
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "authority-diff/1"
    assert "Wrote reach report" in captured.err
    assert "Wrote reach report" not in captured.out


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
