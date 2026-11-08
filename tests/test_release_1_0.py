"""authdiff 1.0.0: clean product identity and version surfaces."""

from __future__ import annotations

from pathlib import Path

from authdiff import __product_version__, __version__
from authdiff.authority_lock import LOCK_VERSION
from authdiff.build import check_demo_fixture_parity, sync_demo_fixture
from authdiff.cli.parser import CORE_PUBLIC_COMMANDS
from authdiff.versioning import package_version, product_version


def test_versions_are_1_0_0() -> None:
    assert __product_version__ == "1.0.0"
    assert __version__ == "1.0.0"
    assert product_version() == "1.0.0"
    assert package_version() == "1.0.0"
    assert LOCK_VERSION == 1
    assert (Path(__file__).resolve().parents[1] / "VERSION").read_text(
        encoding="utf-8"
    ).strip() == ("1.0.0")


def test_public_identity_is_authdiff() -> None:
    assert "demo" in CORE_PUBLIC_COMMANDS
    assert "lock" in CORE_PUBLIC_COMMANDS
    pyproject = (Path(__file__).resolve().parents[1] / "tools" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert 'name = "authdiff"' in pyproject
    assert "aesa-tools" not in pyproject
    assert (Path(__file__).resolve().parents[1] / "tools" / "authdiff").is_dir()
    assert not (Path(__file__).resolve().parents[1] / "tools" / "aesa").exists()


def test_demo_fixture_parity() -> None:
    sync_demo_fixture()
    check_demo_fixture_parity()
