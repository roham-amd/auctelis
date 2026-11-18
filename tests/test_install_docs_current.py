"""AUCT-001 — one documented install command, no stale pins."""

from __future__ import annotations

from pathlib import Path

import pytest

from auctelis import build
from auctelis.build import check_public_install_versions
from auctelis.versioning import product_version


def _fake_repo(tmp_path: Path) -> Path:
    """Every scanned doc exists and shows the one-line install."""
    root = tmp_path / "repo"
    first = "uvx auctelis check\n"
    for rel in build._INSTALL_DOCS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(first, encoding="utf-8")
    return root


def test_current_repo_install_docs_are_current():
    check_public_install_versions(product_version())


def test_stale_git_tag_pin_fails(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path)
    readme = root / "README.md"
    readme.write_text(
        "uvx auctelis check\n"
        "git+https://github.com/roham-amd/auctelis.git@v0.0.1#subdirectory=tools\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match="git-tag pin"):
        check_public_install_versions(product_version())


def test_stale_package_pin_fails(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path)
    install = root / "docs" / "INSTALL.md"
    install.write_text("uvx auctelis check\npip install auctelis==0.0.1\n", encoding="utf-8")
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match="package pin"):
        check_public_install_versions(product_version())


def test_first_run_doc_without_uvx_fails(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path)
    (root / "docs" / "PLAYBOOK.md").write_text("uv tool install auctelis\n", encoding="utf-8")
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match="uvx auctelis"):
        check_public_install_versions(product_version())


def test_no_public_doc_names_a_0_9_pin():
    root = Path(__file__).resolve().parents[1]
    for rel in build._INSTALL_DOCS:
        text = (root / rel).read_text(encoding="utf-8")
        assert "git+https://github.com/roham-amd/auctelis.git@v0.9" not in text
        assert "auctelis==0.9" not in text
