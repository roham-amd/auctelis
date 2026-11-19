"""``auctelis status`` for lockless installs and invalid local state."""

from __future__ import annotations

from pathlib import Path

from auctelis.cli import main


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
        "uses: roham-amd/auctelis/.github/actions/auctelis-gate@v0.16.0\n"
        'with: { locked: "false" }  # add locked: "true" later\n'
    )
    has_gate, locked, pin = _workflow_locked_state(body)
    assert has_gate is True
    assert locked is False
    assert pin == "v0.16.0"


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
