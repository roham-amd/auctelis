"""Inventory must not re-scan authdiff output directories under any suffix."""

from __future__ import annotations

from pathlib import Path

from authdiff.inventory.io import _is_authdiff_output_dir, iter_repo_files
from authdiff.inventory.limits import CollectorLimits


def test_authdiff_output_dir_predicate():
    assert _is_authdiff_output_dir("authdiff-out")
    assert _is_authdiff_output_dir("authdiff-out-pilot")
    assert _is_authdiff_output_dir("authdiff-out-wheel-smoke")
    assert not _is_authdiff_output_dir("authdiff-output")
    assert not _is_authdiff_output_dir("out")


def test_iter_repo_files_skips_authdiff_out_prefix(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "keep").mkdir(parents=True)
    (root / "keep" / "ok.txt").write_text("x\n", encoding="utf-8")
    junk = root / "authdiff-out-pilot"
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
    assert not any(r.startswith("authdiff-out-pilot/") for r in rels)
