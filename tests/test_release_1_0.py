"""authdiff 0.2.0: clean product identity and version surfaces."""

from pathlib import Path

from authdiff import __product_version__, __version__
from authdiff.authority_lock import LOCK_VERSION
from authdiff.versioning import package_version, product_version


def test_version_surfaces_aligned():
    assert __product_version__ == "0.2.0"
    assert __version__ == "0.2.0"
    assert product_version() == "0.2.0"
    assert package_version() == "0.2.0"
    assert LOCK_VERSION == 1
    assert (Path(__file__).resolve().parents[1] / "VERSION").read_text(
        encoding="utf-8"
    ).strip() == ("0.2.0")
