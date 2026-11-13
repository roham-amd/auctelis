"""auctelis version/doc contract surfaces (product + package alignment)."""

import json
from pathlib import Path

from auctelis import __product_version__, __version__
from auctelis.authority_lock import LOCK_VERSION
from auctelis.build import (
    check_bare_command_docs,
    check_install_doc_versions,
    check_policy_schema_contract,
    check_version_metadata,
)
from auctelis.versioning import package_version, product_version

_EXPECTED = "0.3.3"
_ROOT = Path(__file__).resolve().parents[1]


def test_version_surfaces_aligned():
    assert __product_version__ == _EXPECTED
    assert __version__ == _EXPECTED
    assert product_version() == _EXPECTED
    assert package_version() == _EXPECTED
    assert LOCK_VERSION == 1
    assert (_ROOT / "VERSION").read_text(encoding="utf-8").strip() == _EXPECTED


def test_release_manifest_disables_removed_aliases():
    manifest = json.loads(
        (_ROOT / "canonical" / "release-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["product_version"] == _EXPECTED
    assert manifest["package_version"] == _EXPECTED
    assert manifest["contracts"]["policy_contract"] == "1.3"
    assert manifest["interfaces"]["open_alias"] is False
    assert manifest["interfaces"]["fix_alias"] is False


def test_doc_and_policy_contract_checks():
    check_version_metadata()
    check_install_doc_versions(_EXPECTED)
    check_bare_command_docs()
    check_policy_schema_contract()
