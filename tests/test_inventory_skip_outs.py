"""Inventory must not re-scan auctelis output directories under any suffix."""

from __future__ import annotations

from pathlib import Path

from auctelis.inventory.io import _is_auctelis_output_dir, iter_repo_files
from auctelis.inventory.limits import CollectorLimits


def test_auctelis_output_dir_predicate():
    assert _is_auctelis_output_dir("auctelis-out")
    assert _is_auctelis_output_dir("auctelis-out-pilot")
    assert _is_auctelis_output_dir("auctelis-out-wheel-smoke")
    assert not _is_auctelis_output_dir("auctelis-output")
    assert not _is_auctelis_output_dir("out")


def test_iter_repo_files_skips_auctelis_out_prefix(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "keep").mkdir(parents=True)
    (root / "keep" / "ok.txt").write_text("x\n", encoding="utf-8")
    junk = root / "auctelis-out-pilot"
    junk.mkdir()
    (junk / "findings.json").write_text("{}\n", encoding="utf-8")
    events: list[dict] = []
    _limits, files = iter_repo_files(
        root,
        limits=CollectorLimits(),
        events=events,
        default_excludes=False,
    )
    rels = {str(p.relative_to(root)).replace("\\", "/") for p in files}
    assert "keep/ok.txt" in rels
    assert not any(r.startswith("auctelis-out-pilot/") for r in rels)
