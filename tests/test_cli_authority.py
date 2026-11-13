"""CLI surface tests for doctor / vet / ci init / scan policy discovery."""

from __future__ import annotations

from pathlib import Path

from auctelis.cli import main
from auctelis.cli.parser import build_parser, normalize_argv


def test_normalize_argv_defaults_doctor_or_scan(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert normalize_argv([], cwd=empty) == ["doctor"]
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "AUTHORITY.lock").write_text("{}\n", encoding="utf-8")
    assert normalize_argv([], cwd=locked) == ["scan", "."]
    assert normalize_argv(["."]) == ["scan", "."]
    assert normalize_argv(["--locked"]) == ["scan", "--locked"]
    assert normalize_argv(["doctor"]) == ["doctor"]
    assert normalize_argv(["--help"]) == ["--help"]
    assert normalize_argv(["check", "--locked", "."]) == ["check", "--locked", "."]


def test_bare_auctelis_runs_scan(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("x\n", encoding="utf-8")
    code = main([str(root), "-o", str(tmp_path / "out"), "--fail-on", "never"])
    assert code == 0
    assert (tmp_path / "out" / "findings.json").is_file()


def test_product_help_hides_advanced_shows_core():
    help_text = build_parser(include_dev=False).format_help()
    assert "demo" in help_text
    assert "doctor" in help_text
    assert "lock" in help_text
    # Advanced names may appear in the epilog tier list, not as listed commands.
    listed = [
        line
        for line in help_text.splitlines()
        if line.startswith("    ") and not line.strip().startswith("(")
    ]
    listed_text = "\n".join(listed)
    assert "artifact-vet" not in listed_text
    assert "lsp-validate" not in listed_text
    assert "init-manifest" not in listed_text
    # `baseline` command is suppressed; delta may still mention --baseline.
    assert not any(line.strip().startswith("baseline") for line in listed)


def test_cli_doctor_help_and_empty_home(tmp_path: Path, capsys):
    home = tmp_path / "empty-home"
    home.mkdir()
    code = main(["doctor", "--home", str(home)])
    out = capsys.readouterr().out
    assert code == 0
    assert "auctelis doctor" in out or "auctelis doctor" in out
    assert "no host config" in out.lower() or "absent" in out.lower()


def test_cli_ci_init_writes_files(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    code = main(["ci", "init", str(root), "--owner", "@sec-owners"])
    out = capsys.readouterr().out
    assert code == 0
    assert (root / ".auctelis.yml").is_file()
    assert (root / ".github" / "workflows" / "auctelis-gate.yml").is_file()
    workflow = (root / ".github" / "workflows" / "auctelis-gate.yml").read_text(encoding="utf-8")
    assert "trusted-policy" in workflow
    assert 'locked: "false"' in workflow
    assert 'strict-ruleset: "true"' in workflow
    assert "Wrote" in out
    owners = (root / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "@sec-owners" in owners

    code2 = main(["ci", "init", str(root), "--owner", "@sec-owners"])
    out2 = capsys.readouterr().out
    assert code2 == 0
    assert "Exists" in out2


def test_cli_vet_local(tmp_path: Path, capsys):
    root = tmp_path / "pkg"
    skill = root / "skills" / "ok"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: ok\n---\nRead-only helper.\n", encoding="utf-8")
    code = main(["vet", str(root), "-o", str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert "auctelis vet" in out or "auctelis vet" in out
    assert "verdict:" in out
    assert code in {0, 1}


def test_cli_scan_ignores_parent_policy(tmp_path: Path, capsys):
    parent = tmp_path / "parent"
    child = parent / "repo"
    child.mkdir(parents=True)
    (parent / ".auctelis.yml").write_text(
        "version: 1\npolicy:\n  mode: enforce\n  fail_on: high\n",
        encoding="utf-8",
    )
    (child / "README.md").write_text("x\n", encoding="utf-8")
    code = main(["scan", str(child), "-o", str(tmp_path / "out"), "--fail-on", "never"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Policy:" not in out
