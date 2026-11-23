"""CLI wiring for ``auctelis check --github`` (AUCT-022)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from auctelis.github_audit import RepoAuditResult
from auctelis_devtools.cli import main_dev as main


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


def test_github_one_usable_plus_skipped_writes_fleet(tmp_path: Path, capsys):
    """AUCT-027: org audits with skipped rows always emit the fleet report."""
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
        "default_branch": "main",
        "github_web_base": "https://github.com",
    }
    fake = [
        RepoAuditResult(repository="acme/app", report=report, scan=None, cards=[]),
        RepoAuditResult(
            repository="acme/gone",
            skipped=True,
            notes=["repository not found: acme/gone"],
        ),
    ]
    out = tmp_path / "out"
    with patch(
        "auctelis.github_audit.audit_github_repos",
        return_value=(fake, ["acme/app: fetched 0", "acme/gone: skipped"]),
    ) as mocked:
        code = main(["check", "--github", "acme", "--report", str(out)])
        # include_forks defaults false and is forwarded.
        kwargs = mocked.call_args.kwargs
        assert kwargs.get("include_forks") is False
    assert code == 0
    doc = (out / "reach-report.json").read_text(encoding="utf-8")
    assert "auctelis.fleet_reach_report" in doc or '"skipped"' in doc
    assert "acme/gone" in doc
    md = (out / "reach-report.md").read_text(encoding="utf-8")
    assert "Skipped" in md
    assert "acme/gone" in md


def test_github_include_forks_flag_forwarded(tmp_path: Path):
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
    fake = [RepoAuditResult(repository="acme/app", report=report, scan=None, cards=[])]
    with patch(
        "auctelis.github_audit.audit_github_repos",
        return_value=(fake, []),
    ) as mocked:
        main(
            [
                "check",
                "--github",
                "acme/app",
                "--include-forks",
                "--report",
                str(tmp_path / "out"),
            ]
        )
        assert mocked.call_args.kwargs.get("include_forks") is True
