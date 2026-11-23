"""AUCT-069: diff --base surfaces added SECURITY_FINDING red flags + markdown."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from auctelis.cli import main
from auctelis.diff_base import run_diff_base

_REPO = Path(__file__).resolve().parents[1]
_EVIL_SKILL = (
    _REPO / "examples" / "attack-replay" / "05-skill-sudo-pipe" / "evil-bootstrap" / "SKILL.md"
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")


def test_diff_base_surfaces_added_red_flags_and_markdown(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    (root / "README.md").write_text("base\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")

    dest = root / "05-skill-sudo-pipe" / "evil-bootstrap"
    dest.mkdir(parents=True)
    shutil.copy(_EVIL_SKILL, dest / "SKILL.md")

    _text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert code == 1
    rule_ids = {
        (rf.get("rule_id") if isinstance(rf, dict) else getattr(rf, "rule_id", None))
        for rf in (payload.get("red_flags") or [])
    }
    assert "AUCTELIS-RULE-015" in rule_ids

    out = tmp_path / "pr-comment.md"
    cli_code = main(
        [
            "diff",
            "--base",
            "HEAD",
            "--repo",
            str(root),
            "--markdown",
            "--out",
            str(out),
        ]
    )
    assert cli_code == 1
    assert out.is_file()
    assert "AUCTELIS-RULE-015" in out.read_text(encoding="utf-8")
