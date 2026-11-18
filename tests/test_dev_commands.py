"""Maintainer CLI handlers (``auctelis-dev``): routing, lint wrapper, smoke paths.

These commands are not part of the product gate but they are used in CI and by
maintainers, so the dispatch split and error handling deserve their own tests.
All cases here are offline.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from auctelis.cli import dev_commands, main_dev
from auctelis.lint import run_ruff


def _mcp(root: Path) -> None:
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}),
        encoding="utf-8",
    )


def test_require_research_reports_missing_package(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "auctelis_research":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(SystemExit, match="source checkout"):
        dev_commands.require_research()


def _fake_ruff(monkeypatch, tmp_path: Path, returncodes: list[int]) -> list[list[str]]:
    (tmp_path / "tools" / "auctelis").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr("auctelis.lint.repo_root", lambda: tmp_path)
    calls: list[list[str]] = []
    codes = iter(returncodes)

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, next(codes), "out", "")

    monkeypatch.setattr("auctelis.lint.subprocess.run", fake_run)
    return calls


def test_run_ruff_builds_check_and_format_commands(monkeypatch, tmp_path: Path):
    calls = _fake_ruff(monkeypatch, tmp_path, [0, 0])
    summary = run_ruff(fix=True, check_format=True)
    assert summary["ok"] is True
    assert "--fix" in calls[0]
    assert calls[1][-3:] == ["format", "--check", "--config"] or "format" in calls[1]
    assert "format" in calls[1] and "--check" in calls[1]


def test_run_ruff_failure_is_reported(monkeypatch, tmp_path: Path):
    _fake_ruff(monkeypatch, tmp_path, [1])
    summary = run_ruff()
    assert summary["ok"] is False
    assert summary["results"][0]["returncode"] == 1


def test_run_ruff_without_python_roots(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("auctelis.lint.repo_root", lambda: tmp_path / "missing")
    assert run_ruff()["ok"] is False


def test_inventory_command_writes_json(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    _mcp(root)
    out = tmp_path / "inventory.json"
    assert main_dev(["inventory", str(root), "-o", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "components" in payload
    assert "coverage" in payload


def test_verify_digest_command(tmp_path: Path, capsys):
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"auctelis")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    assert main_dev(["verify", "digest", str(path), "--expected", digest]) == 0
    assert "true" in capsys.readouterr().out
    assert main_dev(["verify", "digest", str(path), "--expected", "0" * 64]) == 1
    assert main_dev(["verify", "digest", str(path)]) == 0


def test_hosts_commands(capsys):
    assert main_dev(["hosts", "list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert any(host["host_id"] == "cursor" for host in listed["hosts"])
    assert main_dev(["hosts", "show", "cursor"]) == 0
    assert "cursor" in capsys.readouterr().out
    assert main_dev(["hosts", "show", "not-a-host"]) == 1


def test_export_sarif_command(tmp_path: Path):
    sample = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "validation"
        / "positive"
        / "sample-audit-summary.json"
    )
    out = tmp_path / "findings.sarif.json"
    assert main_dev(["export", "sarif", str(sample), "-o", str(out)]) == 0
    sarif = json.loads(out.read_text(encoding="utf-8"))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"]


def test_export_missing_report_fails_cleanly(tmp_path: Path, capsys):
    assert main_dev(["export", "sarif", str(tmp_path / "nope.json")]) == 1
    assert "Report not found" in capsys.readouterr().out


def test_annotate_missing_findings(tmp_path: Path, capsys):
    assert main_dev(["annotate", str(tmp_path / "nope.json")]) == 1
    assert "Findings not found" in capsys.readouterr().out


def test_annotate_pr_comment_from_minimal_doc(tmp_path: Path, capsys):
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps({"findings": [], "coverage": {}}), encoding="utf-8")
    assert main_dev(["annotate", str(findings), "--format", "pr-comment"]) == 0
    assert "Authority Diff" in capsys.readouterr().out


def test_snapshot_from_file_command(tmp_path: Path, capsys):
    payload = {"tools": [{"name": "read_file", "description": "Read a file"}]}
    path = tmp_path / "tools.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert main_dev(["snapshot", "--from-file", str(path)]) == 0
    assert "read_file" in capsys.readouterr().out


def test_validate_report_invalid_json_fails_closed(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit, match="Invalid JSON"):
        main_dev(["validate", "report", str(path)])


def test_build_schemas_command_keeps_parity(capsys):
    assert main_dev(["build", "schemas"]) == 0


def test_run_command_executes_scrubbed_child(tmp_path: Path):
    code = main_dev(
        [
            "run",
            "--",
            sys.executable,
            "-c",
            "import os; print('broker-ok', os.environ.get('PATH') is not None)",
        ]
    )
    assert code == 0


def test_run_subcommand_keeps_its_command_name():
    from auctelis.cli.parser import build_parser

    args = build_parser(include_dev=True).parse_args(
        ["run", "--", sys.executable, "-c", "print(1)"]
    )
    assert args.command == "run"
    assert args.run_command[:2] == ["--", sys.executable]
