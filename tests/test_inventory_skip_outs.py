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


def test_iter_repo_files_skips_caches_sorted_and_safe_read_guards(tmp_path: Path):
    from auctelis.inventory.io import safe_read_text
    from auctelis_devtools.build import _skip_markdown_path

    root = tmp_path / "repo"
    (root / ".uv-cache").mkdir(parents=True)
    (root / ".uv-cache" / "cached.md").write_text("x\n", encoding="utf-8")
    (root / ".pytest_cache").mkdir(parents=True)
    (root / ".pytest_cache" / "cached.txt").write_text("x\n", encoding="utf-8")
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "big.txt").write_text("x" * 100, encoding="utf-8")

    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")

    events: list[dict] = []
    _summary, files = iter_repo_files(
        root,
        limits=CollectorLimits(max_file_bytes=50),
        events=events,
        default_excludes=False,
    )
    rels = [p.relative_to(root).as_posix() for p in files]
    assert rels == ["a.txt", "b.txt"]
    assert any(e.get("type") == "parse_skipped_size" for e in events)

    escape_events: list[dict] = []
    assert (
        safe_read_text(
            outside, root=root, limits=CollectorLimits(), events=escape_events, adapter="t"
        )
        is None
    )
    assert any(e.get("type") == "path_escape_skipped" for e in escape_events)

    assert _skip_markdown_path(root / ".uv-cache" / "cached.md")
    assert _skip_markdown_path(root / "dist" / "README.md")
