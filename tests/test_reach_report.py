"""AUCT-005 — shareable Agent Reach Report artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auctelis.check import build_check_report, render_check
from auctelis.cli import main
from auctelis.export.reach_report import (
    build_fleet_reach_report,
    build_reach_report,
    diff_reach_reports,
    load_reach_baseline,
    lockless_workflow_yaml,
    render_fleet_reach_html,
    render_fleet_reach_md,
    render_reach_html,
    render_reach_md,
    watch_pr_url,
    write_fleet_reach_report_artifacts,
    write_reach_report_artifacts,
)
from auctelis.inventory.coverage import (
    ADAPTER_COVERAGE,
    family_coverage_line_from_coverage,
    truncation_honesty_notes,
)
from auctelis.versioning import product_version


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
        "product_version": product_version(),
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
        "product_version": product_version(),
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
        assert "Lockless PR Watch" in text or "auctelis.yml" in text
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
        assert "Lockless PR Watch" in text or "auctelis.yml" in text
        # Local-path fleet reports must not invent broken GitHub /new/ links.
        assert "/new/" not in text


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
    code = main(
        [
            "check",
            str(first),
            str(second),
            "--report",
            str(out),
            "--lock-file",
            str(tmp_path / "AUTHORITY.lock"),
        ]
    )
    assert code == 2
    assert "single-repo" in capsys.readouterr().out
    code = main(["check", str(first), str(second), "--report", str(out), "--pins"])
    assert code == 2
    assert "--pins" in capsys.readouterr().out
    assert not out.exists()
    # AUCT-049: --baseline is allowed on fleet when the prior doc is a fleet report.
    prior = tmp_path / "prior"
    assert main(["check", str(first), str(second), "--report", str(prior)]) in {0, 1}
    out2 = tmp_path / "fleet2"
    code = main(
        [
            "check",
            str(first),
            str(second),
            "--report",
            str(out2),
            "--baseline",
            str(prior / "reach-report.json"),
        ]
    )
    assert code in {0, 1}
    doc = json.loads((out2 / "reach-report.json").read_text(encoding="utf-8"))
    assert "baseline_diff" in doc


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
    assert "Lockless PR Watch" in md
    assert "/new/" not in md


def test_watch_pr_url_for_github_slug():
    url = watch_pr_url(
        repository="acme/payments",
        default_branch="main",
        github_web_base="https://github.com",
    )
    assert url is not None
    assert url.startswith("https://github.com/acme/payments/new/main?")
    assert "filename=.github%2Fworkflows%2Fauctelis.yml" in url
    assert f"roham-amd%2Fauctelis%40v{product_version()}" in url or (
        f"auctelis%40v{product_version()}" in url
    )
    assert "value=" in url
    assert "message=" in url
    assert (
        "Add%20auctelis%20lockless%20PR%20Watch%20workflow" in url
        or "Add+auctelis+lockless+PR+Watch+workflow" in url
    )


def test_watch_pr_url_omitted_for_local_path():
    assert (
        watch_pr_url(
            repository="/tmp/repo",
            default_branch="main",
        )
        is None
    )
    assert (
        watch_pr_url(
            repository="acme/app",
            default_branch="../evil",
        )
        is None
    )


def test_github_fleet_report_includes_watch_links_and_skipped():
    pin = f"v{product_version()}"
    assert pin in lockless_workflow_yaml()
    entries = [
        (
            {
                "repository": "acme/payments",
                "default_branch": "main",
                "github_web_base": "https://github.com",
                "coverage_line": "",
                "unparsed": 0,
                "reach": {
                    "total": 1,
                    "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                    "records": [
                        {
                            "kind": "mcp",
                            "name": "evil",
                            "path": ".cursor/mcp.json",
                            "tier": 2,
                            "reason": "new MCP",
                        }
                    ],
                    "top": [],
                    "top_cards": [],
                },
                "pins": {
                    "total": 1,
                    "unpinned": 1,
                    "items": [
                        {
                            "name": "evil",
                            "path": ".cursor/mcp.json",
                            "suggestion": "pin the package: npx -y demo@<exact-version>",
                            "config_snippet": '"args": ["-y", "demo@<exact-version>"]',
                        }
                    ],
                },
                "counts": {},
                "delta": {},
                "label": "NONE",
                "verdict": "BASELINE_NEEDED",
                "schema_version": "authority-diff/1",
                "lock_present": False,
                "first_run": True,
                "meaningful": False,
            },
            None,
            [],
        )
    ]
    doc = build_fleet_reach_report(
        entries,
        skipped=[
            {
                "repository": "acme/private",
                "notes": ["HTTP 403"],
                "skipped": True,
                "truncated": False,
            }
        ],
        honesty_notes=["GitHub API rate limit exhausted — remaining repositories skipped."],
    )
    html = render_fleet_reach_html(doc)
    md = render_fleet_reach_md(doc)
    for text in (html, md):
        assert "acme/payments/new/main" in text or "acme/payments/new/main?" in text
        assert ".github/workflows/auctelis.yml" in text or "auctelis.yml" in text
        assert "Skipped / Incomplete" in text
        assert "acme/private" in text
        assert "rate limit" in text.lower()
        assert "demo@&lt;exact-version&gt;" in text or "demo@<exact-version>" in text
    assert "<script>" not in html
    # Hostile slug must not inject into HTML when rendered via watch helpers.
    hostile = build_reach_report(
        {
            "repository": 'acme/pay"><script>alert(1)</script>',
            "default_branch": "main",
            "github_web_base": "https://github.com",
            "coverage_line": "",
            "unparsed": 0,
            "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}},
            "pins": {},
            "counts": {},
            "delta": {},
            "label": "NONE",
            "verdict": "BASELINE_NEEDED",
            "schema_version": "authority-diff/1",
            "lock_present": False,
            "first_run": True,
            "meaningful": False,
        },
        None,
    )
    hostile_html = render_reach_html(hostile)
    assert "<script>alert(1)</script>" not in hostile_html
    assert "/new/" not in hostile_html  # invalid slug → no watch link


def test_honesty_notes_from_github_truncation_appear_in_single_repo_report():
    """AUCT-027: GitHub tree truncation notes merge into honesty.truncation."""
    doc = build_reach_report(
        {
            "repository": "acme/app",
            "default_branch": "main",
            "github_web_base": "https://github.com",
            "coverage_line": "Coverage: ok",
            "unparsed": 0,
            "honesty_notes": [
                "acme/app: git tree truncated=true — watched-path scan may be incomplete"
            ],
            "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}},
            "pins": {},
            "counts": {},
            "delta": {},
            "label": "NONE",
            "verdict": "BASELINE_NEEDED",
            "schema_version": "authority-diff/1",
            "lock_present": False,
            "first_run": True,
            "meaningful": False,
        },
        None,
    )
    trunc = doc["honesty"]["truncation"]
    assert any("truncated=true" in str(n) for n in trunc)
    md = render_reach_md(doc)
    html = render_reach_html(doc)
    assert "truncated=true" in md
    assert "No walk truncation reported" not in md
    assert "truncated=true" in html


def test_already_watching_suppresses_new_watch_link():
    """AUCT-027: repos with auctelis workflow show Watching, not /new/."""
    doc = build_reach_report(
        {
            "repository": "acme/watched",
            "default_branch": "main",
            "github_web_base": "https://github.com",
            "already_watching": True,
            "coverage_line": "",
            "unparsed": 0,
            "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}},
            "pins": {},
            "counts": {},
            "delta": {},
            "label": "NONE",
            "verdict": "BASELINE_NEEDED",
            "schema_version": "authority-diff/1",
            "lock_present": False,
            "first_run": True,
            "meaningful": False,
        },
        None,
    )
    assert doc["already_watching"] is True
    md = render_reach_md(doc)
    html = render_reach_html(doc)
    assert "Watching" in md
    assert "/new/" not in md
    assert "Watching" in html
    assert "/new/" not in html
    fleet = build_fleet_reach_report(
        [
            (
                {
                    "repository": "acme/watched",
                    "default_branch": "main",
                    "github_web_base": "https://github.com",
                    "already_watching": True,
                    "coverage_line": "",
                    "unparsed": 0,
                    "reach": {
                        "total": 0,
                        "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0},
                    },
                    "pins": {},
                    "counts": {},
                    "delta": {},
                    "label": "NONE",
                    "verdict": "BASELINE_NEEDED",
                    "schema_version": "authority-diff/1",
                    "lock_present": False,
                    "first_run": True,
                    "meaningful": False,
                },
                None,
                [],
            )
        ]
    )
    fleet_md = render_fleet_reach_md(fleet)
    fleet_html = render_fleet_reach_html(fleet)
    assert "Watching" in fleet_md
    assert "acme/watched/new/" not in fleet_md
    assert "Watching" in fleet_html
    assert "acme/watched/new/" not in fleet_html


def test_auct031_local_path_omits_watch_click_copy():
    """AUCT-031: non-GitHub local dirs omit '(or click Watch PRs)'."""
    doc = build_reach_report(
        {
            "repository": str(Path("/tmp/local-repo").resolve()),
            "coverage_line": "",
            "unparsed": 0,
            "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}},
            "pins": {},
            "counts": {},
            "delta": {},
            "label": "NONE",
            "verdict": "BASELINE_NEEDED",
            "schema_version": "authority-diff/1",
            "lock_present": False,
            "first_run": True,
            "meaningful": False,
        },
        None,
    )
    md = render_reach_md(doc)
    html = render_reach_html(doc)
    assert "or click" not in md.lower()
    assert "or click" not in html.lower()
    assert "Watch PRs" not in md or "click **Watch PRs**" not in md


def test_auct031_github_origin_meta_emits_watch_url(tmp_path: Path, monkeypatch):
    """AUCT-031: local GitHub origin yields Watch PRs URL / Watching."""
    from auctelis.github_audit import infer_local_github_watch_meta

    root = (tmp_path / "repo").resolve()
    root.mkdir()
    (root / ".git").mkdir()

    def fake_run(cmd, **kwargs):
        class _P:
            returncode = 0
            stdout = ""
            stderr = ""

        if not isinstance(cmd, (list, tuple)):
            _P.returncode = 1
            return _P()
        # Match git -C <root> …
        if len(cmd) >= 5 and cmd[0] == "git" and cmd[1] == "-C" and Path(cmd[2]).resolve() == root:
            if cmd[3] == "rev-parse" and "--show-toplevel" in cmd:
                _P.stdout = f"{root}\n"
                return _P()
            if cmd[3:5] == ["remote", "get-url"]:
                _P.stdout = "git@github.com:acme/demo.git\n"
                return _P()
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                _P.stdout = "main\n"
                return _P()
        _P.returncode = 1
        return _P()

    monkeypatch.setattr("auctelis.github_audit.subprocess.run", fake_run)
    meta = infer_local_github_watch_meta(root)
    assert meta["repository"] == "acme/demo"
    assert meta["default_branch"] == "main"
    assert meta["already_watching"] is False

    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "auctelis.yaml").write_text("name: auctelis\n", encoding="utf-8")
    meta2 = infer_local_github_watch_meta(root)
    assert meta2["already_watching"] is True

    doc = build_reach_report(
        {
            "repository": "acme/demo",
            "default_branch": "main",
            "github_web_base": "https://github.com",
            "coverage_line": "",
            "unparsed": 0,
            "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}},
            "pins": {},
            "counts": {},
            "delta": {},
            "label": "NONE",
            "verdict": "BASELINE_NEEDED",
            "schema_version": "authority-diff/1",
            "lock_present": False,
            "first_run": True,
            "meaningful": False,
        },
        None,
    )
    md = render_reach_md(doc)
    assert "Watch PRs" in md
    assert "acme/demo/new/main" in md


def test_auct032_fleet_watching_and_org_rollout():
    """AUCT-032: watching KPI + org-reusable / gh rollout for unwatched tier-2."""
    from auctelis.export.reach_report import render_fleet_summary

    entries = [
        (
            {
                "repository": "acme/hot",
                "default_branch": "main",
                "github_web_base": "https://github.com",
                "already_watching": False,
                "coverage_line": "",
                "unparsed": 0,
                "reach": {
                    "total": 1,
                    "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                    "records": [
                        {
                            "kind": "mcp",
                            "name": "evil",
                            "path": ".cursor/mcp.json",
                            "tier": 2,
                            "reason": "new MCP",
                        }
                    ],
                    "top": [],
                    "top_cards": [],
                },
                "pins": {"total": 0, "unpinned": 0, "items": []},
                "counts": {},
                "delta": {},
                "label": "NONE",
                "verdict": "BASELINE_NEEDED",
                "schema_version": "authority-diff/1",
                "lock_present": False,
                "first_run": True,
                "meaningful": False,
            },
            None,
            [],
        ),
        (
            {
                "repository": "acme/watched",
                "default_branch": "main",
                "github_web_base": "https://github.com",
                "already_watching": True,
                "coverage_line": "",
                "unparsed": 0,
                "reach": {
                    "total": 1,
                    "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                    "records": [],
                    "top": [],
                    "top_cards": [],
                },
                "pins": {"total": 0, "unpinned": 0, "items": []},
                "counts": {},
                "delta": {},
                "label": "NONE",
                "verdict": "BASELINE_NEEDED",
                "schema_version": "authority-diff/1",
                "lock_present": False,
                "first_run": True,
                "meaningful": False,
            },
            None,
            [],
        ),
        (
            {
                "repository": 'acme/evil`"; rm -rf /',
                "default_branch": "main",
                "github_web_base": "https://github.com",
                "already_watching": False,
                "coverage_line": "",
                "unparsed": 0,
                "reach": {
                    "total": 1,
                    "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                    "records": [],
                    "top": [],
                    "top_cards": [],
                },
                "pins": {"total": 0, "unpinned": 0, "items": []},
                "counts": {},
                "delta": {},
                "label": "NONE",
                "verdict": "BASELINE_NEEDED",
                "schema_version": "authority-diff/1",
                "lock_present": False,
                "first_run": True,
                "meaningful": False,
            },
            None,
            [],
        ),
    ]
    doc = build_fleet_reach_report(entries)
    assert doc["totals"]["watching"] == 1
    assert doc["totals"]["unwatched_tier2"] == 2
    summary = render_fleet_summary(doc)
    assert "Watching: 1 of 3 repos" in summary
    md = render_fleet_reach_md(doc)
    html = render_fleet_reach_html(doc)
    for text in (md, html):
        assert "Org rollout" in text
        assert "auctelis-org-reusable.yml" in text
        assert "acme/hot" in text
        assert "auctelis rollout" in text
        assert "rollout-watch-prs.sh" not in text
        assert "#!/usr/bin/env bash" not in text
        assert "TARGETS=" not in text
        assert "WORKFLOW_B64" not in text
        assert "fill after reviewing" not in text
    assert "<details>" in html


def test_auct035_fleet_report_omits_watch_script(tmp_path: Path):
    """Fleet reports point at `auctelis rollout` and do not write a Bash script."""
    entries = [
        (
            {
                "repository": "acme/hot",
                "default_branch": "main",
                "github_web_base": "https://github.com",
                "already_watching": False,
                "coverage_line": "",
                "unparsed": 0,
                "reach": {
                    "total": 1,
                    "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                    "records": [],
                    "top": [],
                    "top_cards": [],
                },
                "pins": {"total": 0, "unpinned": 0, "items": []},
                "counts": {},
                "delta": {},
                "label": "NONE",
                "verdict": "BASELINE_NEEDED",
                "schema_version": "authority-diff/1",
                "lock_present": False,
                "first_run": True,
                "meaningful": False,
            },
            None,
            [],
        )
    ]
    out = tmp_path / "fleet"
    write_fleet_reach_report_artifacts(out, entries)
    assert not (out / "rollout-watch-prs.sh").exists()
    text = (out / "reach-report.md").read_text(encoding="utf-8")
    assert "acme/hot" in text
    assert "rollout reach-report.json" in text
    assert "rollout-watch-prs.sh" not in text
    assert f"roham-amd/auctelis@v{product_version()}" in lockless_workflow_yaml()


def test_auct038_org_reusable_rollout_copy(tmp_path: Path):
    """AUCT-038: --org-reusable records the caller in the report, not a Bash script."""
    entries = [
        (
            {
                "repository": "acme/hot",
                "default_branch": "main",
                "github_web_base": "https://github.com",
                "already_watching": False,
                "coverage_line": "",
                "unparsed": 0,
                "reach": {
                    "total": 1,
                    "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                    "records": [],
                    "top": [],
                    "top_cards": [],
                },
                "pins": {"total": 0, "unpinned": 0, "items": []},
                "counts": {},
                "delta": {},
                "label": "NONE",
                "verdict": "BASELINE_NEEDED",
                "schema_version": "authority-diff/1",
                "lock_present": False,
                "first_run": True,
                "meaningful": False,
            },
            None,
            [],
        )
    ]
    out = tmp_path / "fleet"
    write_fleet_reach_report_artifacts(out, entries, org_reusable="acme")
    assert not (out / "rollout-watch-prs.sh").exists()
    md = (out / "reach-report.md").read_text(encoding="utf-8")
    assert "acme/.github/.github/workflows/auctelis-org-reusable.yml@main" in md
    assert "rollout-watch-prs.sh" not in md


def test_auct041_headline_before_honesty():
    """First screen states counts and the worst finding; caveats move down."""
    doc = _parity_doc()
    doc["schema"] = "auctelis.reach_report.v1"
    doc["cards"] = ['+ mcp "demo-evil-mcp"']
    doc["reach"]["top"][0]["name"] = "demo-evil-mcp"
    doc["honesty"]["truncation"] = ["walk truncated=true — watched-path scan may be incomplete"]
    doc["pins"]["items"][0]["name"] = "demo-evil-mcp"
    doc["pins"]["items"][0]["config_snippet"] = '"args": ["-y", "demo-evil-mcp@<exact-version>"]'
    frozen = json.dumps(doc, sort_keys=True)
    md = render_reach_md(doc)
    html = render_reach_html(doc)
    assert json.dumps(doc, sort_keys=True) == frozen
    assert doc["schema"] == "auctelis.reach_report.v1"

    md_lines = md.splitlines()
    head = "\n".join(md_lines[:25])
    first_screen = "\n".join(md_lines[:15])
    assert "at tier 2" in head
    assert "demo-evil-mcp" in head
    assert "not a certificate" in first_screen
    honesty_at = next(i for i, line in enumerate(md_lines) if "Honesty" in line)
    assert honesty_at >= 25
    assert "demo-evil-mcp" in "\n".join(md_lines[:honesty_at])
    summary, _, rest = md.partition("## Coverage and limits")
    assert "truncated=true" in summary
    assert "### Honesty" in rest
    assert "Not auto-inspected" in rest
    assert "DECLARED/CONFIGURED" in rest
    assert '"args": ["-y", "demo-evil-mcp@<exact-version>"]' in summary
    assert "\\[" not in summary.split("**Pin fix:**", 1)[-1].splitlines()[0]

    assert html.index("<h2>Summary</h2>") < html.index("<h2>Tier-2 reach</h2>")
    assert html.index("<h2>Tier-2 reach</h2>") < html.index("<h2>Cards</h2>")
    assert html.index("<h2>Cards</h2>") < html.index("<h2>Coverage and limits</h2>")
    assert html.index("<h2>Coverage and limits</h2>") < html.index("<h3>Honesty</h3>")
    assert html.index("<h3>Honesty</h3>") < html.index("<h3>Not auto-inspected</h3>")
    summary_html, _, _rest_html = html.partition("<h2>Coverage and limits</h2>")
    assert "truncated=true" in summary_html
    assert "not a certificate" in html[: html.index("<h2>Summary</h2>")]


def test_auct043_reach_report_keeps_short_args_and_omits_long_ones():
    """Preserved MCP args render when they fit; over-budget snippets are dropped whole."""
    from auctelis.authority_card import pin_config_snippet
    from auctelis.textutil import PASTEABLE_SNIPPET_MAX

    short = pin_config_snippet(
        {
            "launcher": "npx",
            "pin_state": "floating",
            "args": ["-y", "@scope/mcp", "/workspace"],
        }
    )
    doc = _parity_doc()
    doc["pins"]["items"][0]["config_snippet"] = short
    md = render_reach_md(doc)
    html = render_reach_html(doc)
    assert "/workspace" in md
    assert "/workspace" in html
    assert "**Pin fix:**" in md
    assert "Pin fix" in html

    extra = "w" * 90
    long = pin_config_snippet(
        {
            "launcher": "npx",
            "pin_state": "floating",
            "args": ["-y", "@scope/mcp", "/" + extra],
        }
    )
    assert len(long) > PASTEABLE_SNIPPET_MAX
    assert "…" not in long
    doc["pins"]["items"][0]["config_snippet"] = long
    md_long = render_reach_md(doc)
    html_long = render_reach_html(doc)
    assert "**Pin fix:**" not in md_long
    assert "Pin fix" not in html_long
    assert extra not in md_long
    assert extra not in html_long
    assert long not in md_long


def _resolved_pin_item(*, resolved: bool) -> dict:
    item = {
        "name": "demo",
        "path": ".cursor/mcp.json",
        "pin_state": "floating",
        "suggestion": "pin the package: npx -y @demo/mcp@<exact-version>",
        "config_snippet": '"args": ["-y", "@demo/mcp@<exact-version>"]',
    }
    if resolved:
        item["resolved_pin"] = "@demo/mcp@3.2.1"
        item["resolved_at"] = "2026-11-22"
        item["resolved_suggestion"] = "pin the package: npx -y @demo/mcp@3.2.1"
        item["resolved_config_snippet"] = '"args": ["-y", "@demo/mcp@3.2.1"]'
    return item


def _resolved_single(item: dict) -> dict:
    record = {
        "kind": "MCP Server Registration",
        "name": "demo",
        "path": ".cursor/mcp.json",
        "tier": 2,
        "reason": "secrets",
    }
    return {
        "schema": "auctelis.reach_report.v1",
        "repository": "acme/one",
        "honesty": {"disclaimer": "declared only", "coverage_line": "", "truncation": []},
        "coverage": {"manual_review_families": []},
        "reach": {
            "total": 1,
            "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
            "records": [record],
            "top": [record],
            "top_cards": [],
        },
        "cards": [],
        "pins": {"total": 1, "unpinned": 1, "items": [item]},
    }


def _resolved_fleet(item: dict) -> dict:
    single = _resolved_single(item)
    return {
        "schema": "auctelis.fleet_reach_report.v1",
        "repository_count": 1,
        "totals": {
            "reach_total": 1,
            "tier2": 1,
            "tier1": 0,
            "tier0": 0,
            "unpinned": 1,
            "watching": 0,
            "unwatched_tier2": 1,
        },
        "repositories": [
            {
                "repository": "acme/one",
                "already_watching": False,
                "default_branch": "main",
                "github_web_base": "https://github.com",
                "reach": single["reach"],
                "pins": single["pins"],
            }
        ],
    }


def test_auct051_resolved_pins_in_single_and_fleet_reports():
    """AUCT-051: HTML/MD show resolved pins + TOFU date; default stays placeholder."""
    resolved_item = _resolved_pin_item(resolved=True)
    plain_item = _resolved_pin_item(resolved=False)
    pairs = (
        (render_reach_md, render_reach_html, _resolved_single),
        (render_fleet_reach_md, render_fleet_reach_html, _resolved_fleet),
    )
    for render_md, render_html, build in pairs:
        for text in (render_md(build(resolved_item)), render_html(build(resolved_item))):
            assert "@demo/mcp@3.2.1" in text
            assert "trust-on-first-use: latest on 2026-11-22" in text
            assert "exact-version" not in text
        for text in (render_md(build(plain_item)), render_html(build(plain_item))):
            assert "trust-on-first-use" not in text
            assert "3.2.1" not in text
            assert "exact-version" in text
