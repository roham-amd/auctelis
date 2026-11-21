"""Inventory must ignore pytest-of-* trees under the scanned root."""

from __future__ import annotations

from pathlib import Path

from auctelis.inventory.io import iter_repo_files
from auctelis.inventory.limits import CollectorLimits


def test_iter_repo_files_skips_pytest_of_dirs(tmp_path: Path):
    pollution = tmp_path / "pytest-of-rohaa" / "pytest-0" / "repo" / ".cursor"
    pollution.mkdir(parents=True)
    (pollution / "mcp.json").write_text(
        '{"mcpServers":{"x":{"command":"npx","args":["-y","demo"]}}}',
        encoding="utf-8",
    )
    real = tmp_path / ".cursor"
    real.mkdir()
    (real / "mcp.json").write_text(
        '{"mcpServers":{"ok":{"command":"npx","args":["-y","demo"]}}}',
        encoding="utf-8",
    )
    events: list[dict] = []
    _meta, files = iter_repo_files(
        tmp_path,
        limits=CollectorLimits(),
        events=events,
        default_excludes=False,
    )
    rels = {str(p.relative_to(tmp_path)).replace("\\", "/") for p in files}
    assert ".cursor/mcp.json" in rels
    assert not any(r.startswith("pytest-of-") for r in rels)
