"""``auctelis status`` for lockless installs and invalid local state."""

from __future__ import annotations

from pathlib import Path

from auctelis_devtools.cli import main_dev as main


def _offline(monkeypatch) -> None:
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(name, raising=False)


def test_status_check_accepts_lockless_install(tmp_path: Path, monkeypatch, capsys):
    _offline(monkeypatch)
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["init", str(root), "--lockless"]) == 0
    capsys.readouterr()

    code = main(["status", "--check", str(root)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Workflow: .github/workflows/auctelis.yml" in out
    assert "locked=false" in out
    assert "Lock: missing (OK for lockless comment-only)" in out
    assert "Comment-only ready: YES" in out


def test_status_reports_invalid_policy_and_fails_check(tmp_path: Path, monkeypatch, capsys):
    _offline(monkeypatch)
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".auctelis.yml").write_text("version: 2\n", encoding="utf-8")
    code = main(["status", "--check", str(root)])
    out = capsys.readouterr().out
    assert "Policy: INVALID" in out
    assert code == 1


def test_status_reports_invalid_lock_and_fails_check(tmp_path: Path, monkeypatch, capsys):
    _offline(monkeypatch)
    root = tmp_path / "repo"
    root.mkdir()
    (root / "AUTHORITY.lock").write_text("{not json", encoding="utf-8")
    code = main(["status", "--check", str(root)])
    out = capsys.readouterr().out
    assert "Lock: INVALID" in out
    assert code == 1


def test_workflow_state_ignores_comment_opt_ins():
    from auctelis.cli.dispatch import _workflow_locked_state

    body = (
        "uses: roham-amd/auctelis/.github/actions/auctelis-gate@v0.1.0\n"
        'with: { locked: "false" }  # add locked: "true" later\n'
    )
    has_gate, locked, pin = _workflow_locked_state(body)
    assert has_gate is True
    assert locked is False
    assert pin == "v0.1.0"


def test_workflow_state_recognizes_root_marketplace_action():
    from auctelis.cli.dispatch import _workflow_locked_state

    body = 'uses: roham-amd/auctelis@v0.1.0\nwith: { locked: "false" }\n'
    has_gate, locked, pin = _workflow_locked_state(body)
    assert has_gate is True
    assert locked is False
    assert pin == "v0.1.0"


def test_workflow_state_recognizes_local_root_action(tmp_path: Path):
    """AUCT-028: uses: ./ with root action.yml defining auctelis."""
    from auctelis.cli.dispatch import _workflow_locked_state

    root = tmp_path / "repo"
    root.mkdir()
    (root / "action.yml").write_text(
        "name: auctelis Authority Diff\ndescription: gate\nruns:\n  using: composite\n",
        encoding="utf-8",
    )
    body = 'uses: ./\nwith:\n  locked: "true"\n'
    has_gate, locked, pin = _workflow_locked_state(body, root=root)
    assert has_gate is True
    assert locked is True
    assert pin == "./"


def test_workflow_state_rejects_unrelated_local_action(tmp_path: Path):
    """AUCT-028: uses: ./ without auctelis action.yml stays gate=NO."""
    from auctelis.cli.dispatch import _workflow_locked_state

    root = tmp_path / "repo"
    root.mkdir()
    (root / "action.yml").write_text(
        "name: some-other-action\ndescription: local helper\nruns:\n  using: composite\n",
        encoding="utf-8",
    )
    body = "uses: ./\nwith:\n  path: .\n"
    has_gate, _locked, pin = _workflow_locked_state(body, root=root)
    assert has_gate is False
    assert pin == "(unpinned)"


def test_workflow_state_recognizes_org_reusable_caller():
    """AUCT-028: org reusable workflow_call pin is recognized."""
    from auctelis.cli.dispatch import _workflow_locked_state

    body = (
        "jobs:\n  auctelis:\n"
        "    uses: acme/.github/.github/workflows/auctelis-org-reusable.yml@main\n"
    )
    has_gate, locked, pin = _workflow_locked_state(body)
    assert has_gate is True
    assert locked is False
    assert pin == "main"


def test_status_check_local_root_action_exits_zero(tmp_path: Path, monkeypatch, capsys):
    _offline(monkeypatch)
    root = tmp_path / "repo"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "action.yml").write_text(
        "name: auctelis Authority Diff\ndescription: gate\nruns:\n  using: composite\n",
        encoding="utf-8",
    )
    (root / ".github" / "workflows" / "auctelis-gate.yml").write_text(
        "name: auctelis\non: pull_request\njobs:\n  a:\n    runs-on: ubuntu-latest\n"
        '    steps:\n      - uses: ./\n        with:\n          locked: "false"\n',
        encoding="utf-8",
    )
    code = main(["status", "--check", str(root)])
    out = capsys.readouterr().out
    assert code == 0
    assert "gate=yes" in out
    assert "install=local-root-action" in out


def test_status_check_org_reusable_exits_zero(tmp_path: Path, monkeypatch, capsys):
    _offline(monkeypatch)
    root = tmp_path / "repo"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "auctelis.yml").write_text(
        "name: auctelis\non: pull_request\njobs:\n  auctelis:\n"
        "    uses: acme/.github/.github/workflows/auctelis-org-reusable.yml@v1\n",
        encoding="utf-8",
    )
    code = main(["status", "--check", str(root)])
    out = capsys.readouterr().out
    assert code == 0
    assert "gate=yes" in out
    assert "install=org-reusable" in out
    assert "Action @v1" in out


def test_status_lockless_missing_workflow_suggests_init_lockless(
    tmp_path: Path, monkeypatch, capsys
):
    _offline(monkeypatch)
    root = tmp_path / "repo"
    root.mkdir()
    main(["status", str(root)])
    out = capsys.readouterr().out
    assert "auctelis init --lockless" in out
    assert "templates/" not in out
