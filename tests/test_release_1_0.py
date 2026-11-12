"""authdiff 0.3.1: clean product identity and version surfaces."""

from pathlib import Path

from authdiff import __product_version__, __version__
from authdiff.authority_lock import LOCK_VERSION
from authdiff.versioning import package_version, product_version

_EXPECTED = "0.3.1"


def test_version_surfaces_aligned():
    assert __product_version__ == _EXPECTED
    assert __version__ == _EXPECTED
    assert product_version() == _EXPECTED
    assert package_version() == _EXPECTED
    assert LOCK_VERSION == 1
    assert (Path(__file__).resolve().parents[1] / "VERSION").read_text(
        encoding="utf-8"
    ).strip() == _EXPECTED
