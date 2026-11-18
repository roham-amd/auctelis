"""Version resolution must work from a wheel, a checkout, and a broken install."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError

from auctelis import __version__, versioning


def _missing(tmp_path):
    return tmp_path / "missing"


def test_product_version_falls_back_to_embedded(monkeypatch, tmp_path):
    monkeypatch.setattr(versioning, "version_file_path", lambda: _missing(tmp_path))
    monkeypatch.setattr(versioning, "versions_path", lambda: _missing(tmp_path))
    versioning.load_versions.cache_clear()
    versions = versioning.load_versions()
    assert versions["auctelis_product"] == versioning._EMBEDDED_PRODUCT_VERSION
    assert versioning.product_version() == versioning._EMBEDDED_PRODUCT_VERSION


def test_load_versions_reads_canonical_file(monkeypatch, tmp_path):
    versions = tmp_path / "versions.json"
    versions.write_text('{"auctelis_product": "9.9.9"}', encoding="utf-8")
    monkeypatch.setattr(versioning, "versions_path", lambda: versions)
    versioning.load_versions.cache_clear()
    assert versioning.load_versions()["auctelis_product"] == "9.9.9"
    versioning.load_versions.cache_clear()


def test_package_version_falls_back_to_dunder(monkeypatch):
    def missing_package(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(versioning, "pkg_version", missing_package)
    assert versioning.package_version() == __version__
