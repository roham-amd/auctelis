"""AUCT-001 / AUCT-004 — one documented install command, no stale pins."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auctelis.versioning import product_version
from auctelis_devtools import build
from auctelis_devtools.build import check_public_install_versions


def _fake_repo(tmp_path: Path, *, pypi_live: bool = False) -> Path:
    """Every scanned doc exists with a valid first-run install for pypi_live."""
    root = tmp_path / "repo"
    product = product_version()
    if pypi_live:
        first = "uvx auctelis check\n"
    else:
        first = (
            f'uvx --from "git+https://github.com/roham-amd/auctelis.git@v{product}'
            f'#subdirectory=tools" auctelis check\n'
        )
    for rel in build._INSTALL_DOCS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(first, encoding="utf-8")
    manifest = {
        "manifest_version": "1.0",
        "product_version": product,
        "package_version": product,
        "pypi_live": pypi_live,
        "interfaces": {},
        "contracts": {},
    }
    (root / "canonical").mkdir(parents=True, exist_ok=True)
    (root / "canonical" / "release-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return root


def test_current_repo_install_docs_are_current():
    check_public_install_versions(product_version())


def test_stale_git_tag_pin_fails(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path)
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + "git+https://github.com/roham-amd/auctelis.git@v0.0.1#subdirectory=tools\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match="git-tag pin"):
        check_public_install_versions(product_version())


def test_stale_package_pin_fails(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path)
    install = root / "docs" / "INSTALL.md"
    install.write_text(
        install.read_text(encoding="utf-8") + "pip install auctelis==0.0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match="package pin"):
        check_public_install_versions(product_version())


def test_first_run_doc_without_uvx_from_fails_when_not_live(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path, pypi_live=False)
    (root / "docs" / "PLAYBOOK.md").write_text("uv tool install auctelis\n", encoding="utf-8")
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match="uvx --from"):
        check_public_install_versions(product_version())


def test_once_published_copy_fails_when_not_live(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path, pypi_live=False)
    playbook = root / "docs" / "PLAYBOOK.md"
    playbook.write_text(
        playbook.read_text(encoding="utf-8") + "uvx auctelis check once published also works\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match=r"once published|pypi_live=false"):
        check_public_install_versions(product_version())


def test_pypi_live_requires_bare_uvx(monkeypatch, tmp_path: Path):
    root = _fake_repo(tmp_path, pypi_live=True)
    monkeypatch.setattr(build, "repo_root", lambda: root)
    check_public_install_versions(product_version())


def test_pypi_live_requires_bare_check_before_git_fallback(monkeypatch, tmp_path: Path):
    """AUCT-011: pypi_live=true docs must lead with uvx auctelis check."""
    root = _fake_repo(tmp_path, pypi_live=True)
    product = product_version()
    # Put git-tag install before bare uvx — must fail ordering guard.
    bad = (
        f'uvx --from "git+https://github.com/roham-amd/auctelis.git@v{product}'
        f'#subdirectory=tools" auctelis check\n'
        "uvx auctelis check\n"
    )
    (root / "README.md").write_text(bad, encoding="utf-8")
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match=r"lead with bare|before any"):
        check_public_install_versions(product)


def test_no_public_doc_names_a_0_9_pin():
    root = Path(__file__).resolve().parents[1]
    for rel in build._INSTALL_DOCS:
        text = (root / rel).read_text(encoding="utf-8")
        assert "git+https://github.com/roham-amd/auctelis.git@v0.9" not in text
        assert "auctelis==0.9" not in text


def test_lockless_template_and_action_shallow_skip():
    root = Path(__file__).resolve().parents[1]
    tmpl = (root / "tools" / "auctelis" / "templates" / "auctelis-diff.yml").read_text(
        encoding="utf-8"
    )
    assert "fetch-depth: 0" not in tmpl
    action = (root / ".github" / "actions" / "auctelis-gate" / "action.yml").read_text(
        encoding="utf-8"
    )
    assert "id: path_filter" in action
    assert "steps.path_filter.outputs.skip != 'true'" in action
    assert "--depth=1" in action


def test_trust_copy_does_not_lower_new_mcp_authority():
    """AUCT-015: docs match reach_tiers — trust never lowers new MCP/Hook authority."""
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "CLI-REFERENCE.md").read_text(encoding="utf-8")
    assert "benign MCP" not in text
    section = text.split("## `auctelis trust`", 1)[1].split("\n---", 1)[0]
    assert "network-only" in section
    assert "MCP / Hook / Host Settings" in section


def test_product_md_release_line_matches_version():
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "PRODUCT.md").read_text(encoding="utf-8")
    product = product_version()
    assert f"**Release:** {product}" in text
    assert f"**Package:** `auctelis` {product}" in text


def test_pypi_cutover_readiness_check():
    """AUCT-028: auctelis-dev build pypi-check preflight succeeds on this repo."""
    notes = build.check_pypi_cutover_readiness()
    assert any("publish-pypi.yml" in n for n in notes)
    assert any("console script" in n for n in notes)
