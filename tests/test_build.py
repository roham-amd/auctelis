from pathlib import Path

import pytest

from auctelis import build
from auctelis.build import build_all, check_public_install_versions, check_schema_parity
from auctelis.versioning import product_version


def test_build_all_succeeds():
    result = build_all()
    assert result["status"] == "ok"


def test_schema_parity():
    check_schema_parity()


def test_install_docs_pin_current_release():
    check_public_install_versions(product_version())


def test_check_requires_python_rejects_old_minimum(monkeypatch, tmp_path: Path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.9"\n', encoding="utf-8"
    )
    monkeypatch.setattr(build, "repo_root", lambda: tmp_path)
    with pytest.raises(SystemExit, match="requires-python"):
        build.check_requires_python()


def test_install_doc_version_table_is_required(monkeypatch, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "INSTALL.md").write_text("# Install\n\nno table here\n", encoding="utf-8")
    monkeypatch.setattr(build, "repo_root", lambda: tmp_path)
    with pytest.raises(SystemExit, match="missing version row"):
        build.check_install_doc_versions("0.0.0")


def test_public_install_guard_requires_every_doc(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(build, "repo_root", lambda: tmp_path)
    with pytest.raises(SystemExit, match="Missing public install doc"):
        check_public_install_versions("0.0.0")
