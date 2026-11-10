"""Single source of product / package version resolution.

Works from a git checkout *and* from an installed wheel. Never assumes
``Path(__file__).parents[2]/VERSION`` exists.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

from authdiff.paths import version_file_path, versions_path

# Embedded fallbacks — kept in sync by ``authdiff build`` / release checklist.
_EMBEDDED_PRODUCT_VERSION = "0.2.0"
_EMBEDDED_VERSIONS: dict[str, str] = {
    "authdiff_product": "0.2.0",
    "audit_procedure": "1.0",
    "audit_report_schema": "1.0",
    "ecosystem_graph_schema": "1.0",
    "audit_manifest_schema": "1.0",
    "test_corpus": "0.3.0",
    "agent_benchmark": "0.3.0",
    "agent_benchmark_llm": "0.3.0",
    "rule_quality_pack": "1.2.0",
    "build_tool": "authdiff-0.2.0",
    "findings_contract": "1.2",
    "baseline_contract": "1.3",
    "rule_pack": "1.6",
    "host_profiles": "1.1.0",
    "policy_contract": "1.2",
    "authority_snapshot": "1.0",
    "authority_lock": "1.0",
}


@lru_cache(maxsize=1)
def load_versions() -> dict[str, str]:
    try:
        path = versions_path()
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        pass
    return dict(_EMBEDDED_VERSIONS)


def product_version() -> str:
    try:
        path = version_file_path()
        if path.is_file():
            file_ver = path.read_text(encoding="utf-8").strip()
            if file_ver:
                return file_ver
    except OSError:
        pass
    return load_versions().get("authdiff_product") or _EMBEDDED_PRODUCT_VERSION


def package_version() -> str:
    try:
        return pkg_version("authdiff")
    except PackageNotFoundError:
        from authdiff import __version__

        return __version__
