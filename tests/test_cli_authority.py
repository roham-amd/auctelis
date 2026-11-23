"""CLI surface tests for product front door / ci init / dev scan policy."""

from __future__ import annotations

from pathlib import Path

from auctelis.cli.parser import build_parser, normalize_argv
from auctelis.versioning import product_version
from auctelis_devtools.cli import main_dev
from auctelis_devtools.cli import main_dev as main


def test_normalize_argv_defaults_check_or_scan(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert normalize_argv([], cwd=empty) == ["inspect"]
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "AUTHORITY.lock").write_text("{}\n", encoding="utf-8")
    # Bare is always inspect on the product CLI.
    assert normalize_argv([], cwd=locked) == ["inspect"]
    assert normalize_argv(["."]) == ["inspect", "."]
    assert normalize_argv(["--locked"]) == ["--locked"]
    assert normalize_argv(["--help"]) == ["--help"]
    assert normalize_argv(["check", "."]) == ["check", "."]
    assert normalize_argv(["check", "."], include_dev=True) == ["check", "."]
    assert normalize_argv(["scan", "--locked", "."], include_dev=True) == [
        "scan",
        "--locked",
        ".",
    ]


def test_auctelis_path_runs_check(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("x\n", encoding="utf-8")
    code = main(["check", str(root)])
    # First-run / no lock → exit 0 (BASELINE_NEEDED).
    assert code == 0
    captured = capsys.readouterr().out
    assert "Mode: lockless (no AUTHORITY.lock) · label NONE" in captured
    assert "Inventory: 0 records" in captured


def test_product_help_hides_advanced_shows_core():
    help_text = build_parser(include_dev=False).format_help()
    assert "inspect" in help_text
    assert "diff" in help_text
    listed = [
        line
        for line in help_text.splitlines()
        if line.startswith("    ")
        and not line.startswith("     ")
        and not line.strip().startswith("(")
    ]
    listed_text = "\n".join(listed)
    assert "inspect" in listed_text
    assert "diff" in listed_text
    assert not any(line.strip().startswith("check") for line in listed)
    assert not any(line.strip().startswith("demo") for line in listed)
    assert not any(line.strip().startswith("lock") for line in listed)
    assert not any(line.strip().startswith("gate") for line in listed)

    assert "artifact-vet" not in listed_text
    assert "lsp-validate" not in listed_text
    assert "watch" not in listed_text
    assert "doctor" not in listed_text
    assert "init-manifest" not in listed_text
    # Scanner surfaces are hidden from the default first screen.
    assert not any(line.strip().startswith("scan") for line in listed)
    assert not any(line.strip().startswith("vet") for line in listed)
    # `baseline` command is suppressed; delta may still mention --baseline.
    assert not any(line.strip().startswith("baseline") for line in listed)


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
    assert 'strict-ruleset: "false"' in workflow
    assert "Wrote" in out
    owners = (root / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "@sec-owners" in owners

    code2 = main(["ci", "init", str(root), "--owner", "@sec-owners"])
    out2 = capsys.readouterr().out
    assert code2 == 0
    assert "Exists" in out2


def test_init_lockless_writes_only_workflow(tmp_path: Path, capsys):
    """AUCT-013: one file, no owner, no lock/CODEOWNERS/policy ceremony."""
    root = tmp_path / "repo"
    root.mkdir()
    code = main(["init", str(root), "--lockless"])
    out = capsys.readouterr().out
    assert code == 0
    workflow = root / ".github" / "workflows" / "auctelis.yml"
    assert workflow.is_file()
    body = workflow.read_text(encoding="utf-8")
    assert f"roham-amd/auctelis@v{product_version()}" in body
    assert 'locked: "false"' in body
    # Only the workflow is written.
    assert not (root / ".auctelis.yml").exists()
    assert not (root / ".github" / "CODEOWNERS").exists()
    assert not (root / "AUTHORITY.lock").exists()
    assert "git add .github/workflows/auctelis.yml" in out

    # Re-run without --force keeps the existing file.
    code2 = main(["init", str(root), "--lockless"])
    assert code2 == 0
    assert "Exists (use --force)" in capsys.readouterr().out


def test_init_lockless_rejects_enforce(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    code = main(["init", str(root), "--lockless", "--enforce"])
    assert code == 2
    assert "--lockless" in capsys.readouterr().out
    assert not (root / ".github").exists()


def test_init_lockless_refused_for_agent(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setenv("AUCTELIS_AGENT", "1")
    assert main(["init", str(root), "--lockless"]) == 2
    assert not (root / ".github").exists()


def test_init_without_lockless_still_requires_owner(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["init", str(root)]) == 2
    out = capsys.readouterr().out
    assert "--owner" in out and "--lockless" in out
    assert not (root / ".auctelis.yml").exists()


def test_init_lockless_action_sha_offline(tmp_path: Path, monkeypatch):
    """AUCT-054: --action-sha pins the workflow with no tag lookup."""
    sha = "ab" * 20

    def boom(*_args, **_kwargs):
        raise AssertionError("network")

    monkeypatch.setattr("auctelis.action_pin.resolve_release_commit_sha", boom)
    monkeypatch.setattr("auctelis.action_pin.urllib.request.urlopen", boom)
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["init", str(root), "--lockless", "--action-sha", sha.upper()]) == 0
    body = (root / ".github" / "workflows" / "auctelis.yml").read_text(encoding="utf-8")
    assert f"uses: roham-amd/auctelis@{sha} # v{product_version()}" in body
    assert f"uses: roham-amd/auctelis@v{product_version()}" not in body


def test_init_owner_action_sha_pins_gate(tmp_path: Path, monkeypatch):
    """AUCT-057: --action-sha / --pin-sha work on init --owner [--enforce]."""
    sha = "cd" * 20

    def boom(*_args, **_kwargs):
        raise AssertionError("network")

    monkeypatch.setattr("auctelis.action_pin.resolve_release_commit_sha", boom)
    monkeypatch.setattr("auctelis.action_pin.urllib.request.urlopen", boom)
    root = tmp_path / "repo"
    root.mkdir()
    assert (
        main(
            [
                "init",
                str(root),
                "--owner",
                "@sec",
                "--enforce",
                "--action-sha",
                sha.upper(),
            ]
        )
        == 0
    )
    body = (root / ".github" / "workflows" / "auctelis-gate.yml").read_text(encoding="utf-8")
    assert f"uses: roham-amd/auctelis@{sha} # v{product_version()}" in body
    assert f"uses: roham-amd/auctelis@v{product_version()}" not in body
    assert 'locked: "true"' in body


def test_init_owner_pin_sha_resolves_tag(tmp_path: Path, monkeypatch):
    sha = "ef" * 20
    monkeypatch.setattr(
        "auctelis.action_pin.resolve_release_commit_sha",
        lambda _version: (sha, "ok"),
    )
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["init", str(root), "--owner", "sec", "--pin-sha"]) == 0
    body = (root / ".github" / "workflows" / "auctelis-gate.yml").read_text(encoding="utf-8")
    assert f"uses: roham-amd/auctelis@{sha} # v{product_version()}" in body


def test_init_owner_action_sha_invalid_exits_2(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["init", str(root), "--owner", "@sec", "--action-sha", "zz"]) == 2
    assert "40-character" in capsys.readouterr().out
    assert not (root / ".github" / "workflows" / "auctelis-gate.yml").exists()


def test_init_lockless_action_sha_invalid_exits_2(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["init", str(root), "--lockless", "--action-sha", "zz"]) == 2
    assert "40-character" in capsys.readouterr().out
    assert not (root / ".github").exists()


def test_init_lockless_force_rewrites_and_ci_alias_is_equivalent(tmp_path: Path, capsys):
    """The legacy ``ci init`` alias reaches the same lockless writer."""
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["ci", "init", str(root), "--lockless"]) == 0
    workflow = root / ".github" / "workflows" / "auctelis.yml"
    assert workflow.is_file()
    assert not (root / ".auctelis.yml").exists()
    first = workflow.read_text(encoding="utf-8")

    assert main(["init", str(root), "--lockless", "--force"]) == 0
    assert workflow.read_text(encoding="utf-8") == first
    out = capsys.readouterr().out
    assert "Wrote:" in out


def test_cli_scan_ignores_parent_policy(tmp_path: Path, capsys):
    parent = tmp_path / "parent"
    child = parent / "repo"
    child.mkdir(parents=True)
    (parent / ".auctelis.yml").write_text(
        "version: 1\npolicy:\n  mode: enforce\n  fail_on: high\n",
        encoding="utf-8",
    )
    (child / "README.md").write_text("x\n", encoding="utf-8")
    code = main_dev(["scan", str(child), "-o", str(tmp_path / "out"), "--fail-on", "never"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Policy:" not in out


def test_cli_check_json_pins_and_why(tmp_path: Path, capsys):
    import json

    root = tmp_path / "repo"
    (root / ".cursor").mkdir(parents=True)
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"demo": {"command": "npx", "args": ["-y", "demo-pkg"]}}}),
        encoding="utf-8",
    )

    assert main(["check", str(root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "authority-diff/1"

    assert main(["check", str(root), "--pins"]) == 0
    pins_out = capsys.readouterr().out
    assert "Unpinned MCP servers" in pins_out

    assert main(["why", "demo", str(root)]) == 0
    why_out = capsys.readouterr().out
    assert ".cursor/mcp.json" in why_out

    assert main(["why", "nonexistent", str(root)]) == 1
    capsys.readouterr()
