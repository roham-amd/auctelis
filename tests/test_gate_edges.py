"""Gate fail-closed paths and report rendering variants not covered elsewhere."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.gate import render_gate_report, run_gate


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


def _empty_lock(tmp_path: Path) -> Path:
    from auctelis.lock_io import compute_lock_hash

    lock = {"version": 1, "records": [], "mcp_tools": {}}
    lock["lock_hash"] = compute_lock_hash(lock)
    path = tmp_path / "base.lock"
    path.write_text(json.dumps(lock), encoding="utf-8")
    return path


def test_truncation_survives_the_capped_parser_event_list(tmp_path: Path):
    """The gate must not re-derive truncation from ``parser_events[:50]``."""
    from auctelis.inventory.coverage import summarize_coverage
    from auctelis.security.engine import run_authority_inventory

    root = _root(tmp_path)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    scan = run_authority_inventory(root)
    events = [{"type": "default_exclude"} for _ in range(60)]
    events.append({"type": "depth_limit", "path": "deep/"})
    scan.coverage = summarize_coverage([], parser_events=events)
    assert scan.coverage["truncated"] is True
    assert len(scan.coverage["parser_events"]) == 50

    report, code = run_gate(
        root,
        base_lock=_empty_lock(tmp_path),
        scan=scan,
        check_ruleset=False,
        trust_head_codeowners=True,
    )
    assert report["verdict"] == "NEEDS_REVIEW"
    assert "inventory truncated" in str(report.get("error") or "")
    assert code == 1


def test_missing_base_lock_fails_closed(tmp_path: Path):
    report, code = run_gate(_root(tmp_path), base_lock=tmp_path / "missing.lock")
    assert code == 2
    assert report["verdict"] == "FAIL_CLOSED"
    assert "cannot read base lock" in report["error"]


def test_invalid_base_lock_fails_closed(tmp_path: Path):
    bad = tmp_path / "bad.lock"
    bad.write_text("{not json", encoding="utf-8")
    report, code = run_gate(_root(tmp_path), base_lock=bad)
    assert code == 2
    assert report["verdict"] == "FAIL_CLOSED"


def test_missing_head_lock_fails_closed(tmp_path: Path):
    report, code = run_gate(
        _root(tmp_path),
        base_lock=_empty_lock(tmp_path),
        head_lock=tmp_path / "missing-head.lock",
    )
    assert code == 2
    assert report["verdict"] == "FAIL_CLOSED"
    assert "head lock not found" in report["error"]


def test_render_baseline_adopted_report():
    text = render_gate_report(
        {
            "verdict": "BASELINE_ADOPTED",
            "ceremony": "baseline_adopted",
            "label": "NONE",
            "ok": True,
            "lines": [],
            "message": "First lock adoption.",
        }
    )
    assert "BASELINE_ADOPTED" in text
    assert "adoption ceremony" in text
    assert "First lock adoption." in text


def test_render_comment_only_needs_review_header():
    text = render_gate_report(
        {
            "verdict": "NEEDS_REVIEW",
            "mode": "comment-only",
            "label": "GROWTH",
            "ok": True,
            "lines": [],
        }
    )
    assert "NEEDS_REVIEW" in text
    assert "comment-only" in text


def test_render_reduction_and_representation_notes():
    reduction = render_gate_report(
        {"verdict": "PASS", "label": "REDUCTION", "ok": True, "lines": []}
    )
    assert "reduced" in reduction
    representation = render_gate_report(
        {
            "verdict": "PASS",
            "label": "NONE",
            "ok": True,
            "representation_only": True,
            "lines": [],
        }
    )
    assert "not material reach" in representation


def test_codeowners_glob_directory_boundary_and_fail_closed_paths(tmp_path):
    from auctelis.authority_lock import write_authority_lock
    from auctelis.gate import codeowners_covers_path, run_gate

    owners = ".github/workflows/** @sec\n.github/actions/**/* @sec\n"
    assert codeowners_covers_path(owners, ".github/workflows/ci.yml")
    assert not codeowners_covers_path(owners, ".github/workflows-evil/ci.yml")
    assert codeowners_covers_path(owners, ".github/actions/auctelis/action.yml")
    assert not codeowners_covers_path(owners, ".github/actions-evil/action.yml")

    repo = tmp_path / "repo"
    repo.mkdir()
    report_dir, code_dir = run_gate(repo, base_lock=repo)
    assert code_dir == 2
    assert report_dir["verdict"] == "FAIL_CLOSED"

    base_lock, _ = write_authority_lock(repo, path=tmp_path / "base.lock")
    report_missing, code_missing = run_gate(
        repo,
        base_lock=base_lock,
        head_lock=tmp_path / "missing.lock",
    )
    assert code_missing == 2
    assert report_missing["verdict"] == "FAIL_CLOSED"
