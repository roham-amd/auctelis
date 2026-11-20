"""CLI wiring for ``auctelis check --github`` (AUCT-022)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from auctelis.cli import main
from auctelis.github_audit import RepoAuditResult


def test_github_org_requires_report(capsys):
    code = main(["check", "--github", "acme"])
    out = capsys.readouterr().out
    assert code == 2
    assert "--report" in out


def test_github_single_repo_without_report(capsys):
    report = {
        "schema_version": "authority-diff/1",
        "repository": "acme/app",
        "lock_present": False,
        "first_run": True,
        "verdict": "BASELINE_NEEDED",
        "label": "NONE",
        "meaningful": False,
        "unparsed": 0,
        "gated_findings": 0,
        "counts": {},
        "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}},
        "pins": {"total": 0, "unpinned": 0, "items": []},
        "inventory_total": 0,
        "coverage_line": "",
        "error": None,
    }
    fake = [
        RepoAuditResult(repository="acme/app", report=report, scan=None, cards=[]),
    ]
    with patch(
        "auctelis.github_audit.audit_github_repos",
        return_value=(fake, ["acme/app: fetched 0 watched file(s)"]),
    ):
        code = main(["check", "--github", "acme/app"])
    captured = capsys.readouterr()
    assert code == 0
    assert "auctelis check" in captured.out
    assert "BASELINE_NEEDED" in captured.out or "lockless" in captured.out.lower()


def test_github_rejects_lock_file(tmp_path: Path, capsys):
    code = main(
        [
            "check",
            "--github",
            "acme/app",
            "--report",
            str(tmp_path / "out"),
            "--lock-file",
            str(tmp_path / "AUTHORITY.lock"),
        ]
    )
    assert code == 2
    assert "--lock-file" in capsys.readouterr().out


def test_github_rejects_local_path_combo(tmp_path: Path, capsys):
    repo = tmp_path / "local"
    repo.mkdir()
    code = main(
        [
            "check",
            str(repo),
            "--github",
            "acme/app",
            "--report",
            str(tmp_path / "out"),
        ]
    )
    assert code == 2
    assert "cannot be combined" in capsys.readouterr().out


def test_github_single_repo_writes_report(tmp_path: Path, capsys):
    report = {
        "schema_version": "authority-diff/1",
        "repository": "acme/app",
        "lock_present": False,
        "first_run": True,
        "verdict": "BASELINE_NEEDED",
        "label": "NONE",
        "meaningful": False,
        "unparsed": 0,
        "gated_findings": 0,
        "counts": {},
        "reach": {"total": 0, "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0}},
        "pins": {"total": 0, "unpinned": 0, "items": []},
        "inventory_total": 0,
        "coverage_line": "",
        "error": None,
    }
    fake = [
        RepoAuditResult(repository="acme/app", report=report, scan=None, cards=[]),
    ]
    with patch(
        "auctelis.github_audit.audit_github_repos",
        return_value=(fake, ["acme/app: fetched 0 watched file(s)"]),
    ):
        code = main(["check", "--github", "acme/app", "--report", str(tmp_path / "out"), "--json"])
    captured = capsys.readouterr()
    assert code == 0
    assert (tmp_path / "out" / "reach-report.json").is_file()
    assert "acme/app" in captured.out
