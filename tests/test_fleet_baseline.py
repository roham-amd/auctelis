"""AUCT-049 — fleet audit memory (`--baseline`)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from auctelis.cli import main
from auctelis.export.reach_report import (
    diff_fleet_reports,
    render_fleet_reach_html,
    render_fleet_reach_md,
    render_fleet_summary,
    write_fleet_reach_report_artifacts,
)
from auctelis.github_audit import RepoAuditResult


def _repo_doc(slug: str, *, name: str, tier: int, reason: str) -> dict:
    return {
        "repository": slug,
        "default_branch": "main",
        "github_web_base": "https://github.com",
        "already_watching": False,
        "coverage_line": "",
        "unparsed": 0,
        "reach": {
            "total": 1,
            "tier_counts": {
                "tier0": 0 if tier else 1,
                "tier1": 1 if tier == 1 else 0,
                "tier2": 1 if tier == 2 else 0,
            },
            "records": [
                {
                    "kind": "mcp",
                    "name": name,
                    "path": ".cursor/mcp.json",
                    "tier": tier,
                    "reason": reason,
                    "identity_key": f"|mcp|{name}",
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
    }


def test_diff_fleet_added_removed_changed():
    before = {
        "schema": "auctelis.fleet_reach_report.v1",
        "repositories": [
            _repo_doc("acme/a", name="keep", tier=1, reason="net"),
            _repo_doc("acme/gone", name="old", tier=2, reason="secrets"),
        ],
    }
    after = {
        "schema": "auctelis.fleet_reach_report.v1",
        "repositories": [
            _repo_doc("acme/a", name="keep", tier=2, reason="secrets"),
            _repo_doc("acme/new", name="fresh", tier=2, reason="secrets"),
        ],
    }
    diff = diff_fleet_reports(before, after)
    assert [r["repository"] for r in diff["added_repositories"]] == ["acme/new"]
    assert [r["repository"] for r in diff["removed_repositories"]] == ["acme/gone"]
    assert len(diff["repositories"]) == 1
    assert diff["repositories"][0]["repository"] == "acme/a"
    assert len(diff["repositories"][0]["changed"]) == 1


def test_fleet_baseline_section_and_json(tmp_path: Path):
    before_entries = [
        (_repo_doc("acme/a", name="keep", tier=1, reason="net"), None, []),
    ]
    after_entries = [
        (_repo_doc("acme/a", name="keep", tier=2, reason="secrets"), None, []),
        (_repo_doc("acme/b", name="new", tier=2, reason="secrets"), None, []),
    ]
    baseline_dir = tmp_path / "before"
    write_fleet_reach_report_artifacts(baseline_dir, before_entries)
    baseline = json.loads((baseline_dir / "reach-report.json").read_text(encoding="utf-8"))

    out = tmp_path / "after"
    no_base = write_fleet_reach_report_artifacts(out / "plain", after_entries)
    assert "baseline_diff" not in no_base
    md_plain = (out / "plain" / "reach-report.md").read_text(encoding="utf-8")
    html_plain = (out / "plain" / "reach-report.html").read_text(encoding="utf-8")
    assert "Changed since last audit" not in md_plain
    assert "Changed since last audit" not in html_plain

    with_base = write_fleet_reach_report_artifacts(out / "diffed", after_entries, baseline=baseline)
    assert "baseline_diff" in with_base
    md = (out / "diffed" / "reach-report.md").read_text(encoding="utf-8")
    html = (out / "diffed" / "reach-report.html").read_text(encoding="utf-8")
    summary = render_fleet_summary(with_base)
    assert "Changed since last audit" in md
    assert "Changed since last audit" in html
    assert "Changed since last audit" in summary
    assert "acme/b" in md
    assert md.index("## Summary") < md.index("Changed since last audit")
    assert "Coverage and limits" in md
    assert md.index("Changed since last audit") < md.index("Coverage and limits")


def test_fleet_no_baseline_render_matches_helper():
    from auctelis.export.reach_report import build_fleet_reach_report

    entries = [(_repo_doc("acme/a", name="x", tier=2, reason="secrets"), None, [])]
    built = build_fleet_reach_report(entries)
    assert render_fleet_reach_md(built) == render_fleet_reach_md(built, baseline_diff=None)
    assert render_fleet_reach_html(built) == render_fleet_reach_html(built, baseline_diff=None)


def test_github_baseline_fleet(tmp_path: Path):
    report_a = _repo_doc("acme/app", name="keep", tier=1, reason="net")
    report_b = _repo_doc("acme/app", name="keep", tier=2, reason="secrets")
    write_fleet_reach_report_artifacts(
        tmp_path / "base",
        [(report_a, None, [])],
    )
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        (tmp_path / "base" / "reach-report.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fake = [
        RepoAuditResult(repository="acme/app", report=report_b, scan=None, cards=[]),
        RepoAuditResult(
            repository="acme/other",
            report=_repo_doc("acme/other", name="n", tier=2, reason="secrets"),
            scan=None,
            cards=[],
        ),
    ]
    out = tmp_path / "out"
    with patch(
        "auctelis.github_audit.audit_github_repos",
        return_value=(fake, []),
    ):
        code = main(
            [
                "check",
                "--github",
                "acme",
                "--report",
                str(out),
                "--baseline",
                str(baseline_path),
            ]
        )
    assert code in {0, 1}
    doc = json.loads((out / "reach-report.json").read_text(encoding="utf-8"))
    assert "baseline_diff" in doc
    md = (out / "reach-report.md").read_text(encoding="utf-8")
    assert "Changed since last audit" in md


def test_render_fleet_drift_issue_md_none_on_zero_and_marker_on_drift(tmp_path: Path):
    from auctelis.export.reach_report import render_fleet_drift_issue_md

    assert render_fleet_drift_issue_md({}) is None
    assert (
        render_fleet_drift_issue_md(
            {
                "baseline_diff": {
                    "changed_count": 0,
                    "added_repositories": [{"repository": "acme/ignored"}],
                    "removed_repositories": [],
                    "repositories": [],
                }
            }
        )
        is None
    )

    # AUCT-055: Watch self-install / tier-0 alone must stay silent.
    watch_only = {
        "repositories": [
            {
                "repository": "acme/watch",
                "already_watching": True,
                "reach": {
                    "total": 1,
                    "tier_counts": {"tier0": 1, "tier1": 0, "tier2": 0},
                    "records": [
                        {
                            "kind": "CI Workflow",
                            "name": "auctelis",
                            "path": ".github/workflows/auctelis.yml",
                            "tier": 0,
                            "reason": "ci",
                            "identity_key": "|CI Workflow|auctelis",
                        }
                    ],
                },
            }
        ],
        "baseline_diff": {
            "changed_count": 1,
            "added_repositories": [],
            "removed_repositories": [],
            "repositories": [
                {
                    "repository": "acme/watch",
                    "added": [
                        {
                            "kind": "CI Workflow",
                            "name": "auctelis",
                            "path": ".github/workflows/auctelis.yml",
                            "tier": 0,
                            "reason": "ci",
                        }
                    ],
                    "removed": [],
                    "changed": [],
                    "changed_count": 1,
                }
            ],
        },
    }
    assert render_fleet_drift_issue_md(watch_only) is None

    prose_only = {
        "repositories": [
            _repo_doc("acme/prose", name="style", tier=0, reason="prose"),
        ],
        "baseline_diff": {
            "changed_count": 1,
            "added_repositories": [{"repository": "acme/prose"}],
            "removed_repositories": [],
            "repositories": [],
        },
    }
    assert render_fleet_drift_issue_md(prose_only) is None

    drifted = {
        "repositories": [
            _repo_doc("acme/new", name="fresh", tier=2, reason="secrets"),
            _repo_doc("acme/a", name="keep", tier=2, reason="secrets"),
        ],
        "baseline_diff": {
            "changed_count": 2,
            "added_repositories": [{"repository": "acme/new"}],
            "removed_repositories": [{"repository": "acme/gone"}],
            "repositories": [
                {
                    "repository": "acme/a",
                    "added": [],
                    "removed": [],
                    "changed": [
                        {
                            "before": {
                                "kind": "mcp",
                                "name": "keep",
                                "path": ".cursor/mcp.json",
                                "tier": 1,
                                "reason": "net",
                            },
                            "after": {
                                "kind": "mcp",
                                "name": "keep",
                                "path": ".cursor/mcp.json",
                                "tier": 2,
                                "reason": "secrets",
                            },
                        }
                    ],
                    "changed_count": 1,
                }
            ],
        },
    }
    md = render_fleet_drift_issue_md(drifted)
    assert md is not None
    assert md.startswith("<!-- auctelis-org-drift -->")
    assert "acme/new" in md
    assert "acme/a" in md
    assert "tier 1→2" in md or "tier 2" in md
    assert "keep" in md
    assert len(md.splitlines()) <= 25
    # Whole-repo removals stay out of the sticky Issue (no after-side tiers).
    assert "acme/gone" not in md

    # Removed tier≥1 records still page (good-news / shrink signal).
    removed_tier2 = {
        "repositories": [_repo_doc("acme/a", name="keep", tier=0, reason="gone")],
        "baseline_diff": {
            "changed_count": 1,
            "added_repositories": [],
            "removed_repositories": [],
            "repositories": [
                {
                    "repository": "acme/a",
                    "added": [],
                    "removed": [
                        {
                            "kind": "mcp",
                            "name": "gone-server",
                            "path": ".cursor/mcp.json",
                            "tier": 2,
                            "reason": "secrets",
                        }
                    ],
                    "changed": [],
                    "changed_count": 1,
                }
            ],
        },
    }
    removed_md = render_fleet_drift_issue_md(removed_tier2)
    assert removed_md is not None
    assert "gone-server" in removed_md
    assert "tier 2" in removed_md

    # Fleet --report writes org-drift-issue.md only when material reach changed.
    before = [(_repo_doc("acme/a", name="keep", tier=1, reason="net"), None, [])]
    after = [
        (_repo_doc("acme/a", name="keep", tier=2, reason="secrets"), None, []),
        (_repo_doc("acme/b", name="new", tier=2, reason="secrets"), None, []),
    ]
    base_dir = tmp_path / "base"
    write_fleet_reach_report_artifacts(base_dir, before)
    baseline = json.loads((base_dir / "reach-report.json").read_text(encoding="utf-8"))
    plain = tmp_path / "plain"
    write_fleet_reach_report_artifacts(plain, after)
    assert not (plain / "org-drift-issue.md").exists()
    diffed = tmp_path / "diffed"
    write_fleet_reach_report_artifacts(diffed, after, baseline=baseline)
    issue = (diffed / "org-drift-issue.md").read_text(encoding="utf-8")
    assert issue.startswith("<!-- auctelis-org-drift -->")
    assert "acme/b" in issue
    assert len(issue.splitlines()) <= 25


def test_baseline_schema_mismatch_exit_2(tmp_path: Path, capsys):
    single = tmp_path / "single.json"
    single.write_text(
        json.dumps(
            {
                "schema": "auctelis.reach_report.v1",
                "repository": "acme/a",
                "reach": {"total": 0, "tier_counts": {}, "records": []},
            }
        ),
        encoding="utf-8",
    )
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    r1.mkdir()
    r2.mkdir()
    code = main(
        [
            "check",
            str(r1),
            str(r2),
            "--report",
            str(tmp_path / "out"),
            "--baseline",
            str(single),
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "fleet" in (captured.out + captured.err).lower()
