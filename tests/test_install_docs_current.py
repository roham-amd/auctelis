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
        first = "uvx auctelis inspect\n"
    else:
        first = (
            f'uvx --from "git+https://github.com/roham-amd/auctelis.git@v{product}'
            f'#subdirectory=tools" auctelis inspect\n'
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


def test_readme_leads_with_inspect_and_has_uv_prereq():
    """AUCT-071: README leads with inspect / --local and names the uv prerequisite."""
    root = Path(__file__).resolve().parents[1]
    text = (root / "README.md").read_text(encoding="utf-8")
    assert "uvx --from" in text
    assert "auctelis inspect" in text
    assert "inspect --local" in text
    assert "docs.astral.sh/uv" in text
    assert "sample-reach-report.html" not in text
    assert "auctelis rollout" not in text


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
    """AUCT-039: bare `uvx auctelis inspect` is primary; git+ may follow it."""
    root = _fake_repo(tmp_path, pypi_live=True)
    product = product_version()
    primary = (
        "uvx auctelis inspect\n"
        f'uvx --from "git+https://github.com/roham-amd/auctelis.git@v{product}'
        f'#subdirectory=tools" auctelis check\n'
    )
    for rel in build._FIRST_RUN_DOCS:
        (root / rel).write_text(primary, encoding="utf-8")
    monkeypatch.setattr(build, "repo_root", lambda: root)
    check_public_install_versions(product)


def test_auct036_pypi_check_live_http_200(monkeypatch, tmp_path: Path):
    """AUCT-036: --live probes PyPI; HTTP 200 is fine while pypi_live=false."""
    root = _fake_repo(tmp_path, pypi_live=False)
    monkeypatch.setattr(build, "repo_root", lambda: root)
    monkeypatch.setattr(build, "_pypi_live", lambda: False)
    monkeypatch.setattr(build, "check_wheel_omits_research", lambda: ["ok wheel"])
    publish = root / ".github" / "workflows" / "publish-pypi.yml"
    publish.parent.mkdir(parents=True, exist_ok=True)
    publish.write_text(
        "permissions:\n  id-token: write\nenvironment: pypi\n"
        "steps:\n  - run: uv publish\n  - run: curl -fsS https://pypi.org/pypi/auctelis/json\n",
        encoding="utf-8",
    )
    (root / "tools").mkdir(exist_ok=True)
    (root / "tools" / "pyproject.toml").write_text(
        '[project.scripts]\nauctelis = "auctelis.cli:main"\n',
        encoding="utf-8",
    )

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _Resp(),
    )
    notes = build.check_pypi_cutover_readiness(live=True)
    assert any("HTTP 200" in n for n in notes)


def test_auct036_pypi_check_live_fails_when_live_flag_and_pypi_true_404(
    monkeypatch, tmp_path: Path
):
    import urllib.error

    root = _fake_repo(tmp_path, pypi_live=True)
    monkeypatch.setattr(build, "repo_root", lambda: root)
    monkeypatch.setattr(build, "_pypi_live", lambda: True)
    monkeypatch.setattr(build, "check_wheel_omits_research", lambda: ["ok wheel"])
    publish = root / ".github" / "workflows" / "publish-pypi.yml"
    publish.parent.mkdir(parents=True, exist_ok=True)
    publish.write_text(
        "permissions:\n  id-token: write\nenvironment: pypi\n"
        "steps:\n  - run: uv publish\n  - run: curl -fsS https://pypi.org/pypi/auctelis/json\n",
        encoding="utf-8",
    )
    (root / "tools").mkdir(exist_ok=True)
    (root / "tools" / "pyproject.toml").write_text(
        '[project.scripts]\nauctelis = "auctelis.cli:main"\n',
        encoding="utf-8",
    )

    def _raise(*a, **k):
        ver = product_version()
        raise urllib.error.HTTPError(
            url=f"https://pypi.org/pypi/auctelis/{ver}/json",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    with pytest.raises(SystemExit, match=r"pypi_live=true.*HTTP 404"):
        build.check_pypi_cutover_readiness(live=True)


def test_pypi_live_requires_bare_check_before_git_fallback(monkeypatch, tmp_path: Path):
    """AUCT-011: pypi_live=true docs must lead with uvx auctelis inspect."""
    root = _fake_repo(tmp_path, pypi_live=True)
    product = product_version()
    # Put git-tag install before bare uvx — must fail ordering guard.
    bad = (
        f'uvx --from "git+https://github.com/roham-amd/auctelis.git@v{product}'
        f'#subdirectory=tools" auctelis check\n'
        "uvx auctelis inspect\n"
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


def test_auct057_checkout_sha_aligned_across_templates():
    """AUCT-057/058: lockless/gate/consumer-gate share checkout SHA."""
    root = Path(__file__).resolve().parents[1]
    diff = (root / "tools" / "auctelis" / "templates" / "auctelis-diff.yml").read_text(
        encoding="utf-8"
    )
    gate = (root / "tools" / "auctelis" / "templates" / "auctelis-gate.yml").read_text(
        encoding="utf-8"
    )
    consumer = (root / "docs" / "auctelis-consumer-gate.example.yml").read_text(encoding="utf-8")
    pin = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    assert pin in diff
    assert pin in gate
    assert pin in consumer
    assert "# v7.0.1" in consumer
    assert "11bd71901bbe5b1630ceea73d27597364c9af683" not in diff
    assert "11bd71901bbe5b1630ceea73d27597364c9af683" not in gate
    assert "11bd71901bbe5b1630ceea73d27597364c9af683" not in consumer


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


def test_auct033_dogfood_lock_freshness_fails_on_stale_lock(monkeypatch, tmp_path: Path):
    """AUCT-033: build all preflight fails when AUTHORITY.lock digests drift."""
    from auctelis.authority_lock import write_authority_lock

    root = tmp_path / "repo"
    root.mkdir()
    cursor = root / ".cursor"
    cursor.mkdir()
    (cursor / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}) + "\n",
        encoding="utf-8",
    )
    write_authority_lock(root, accept_gated=True)
    # Representation drift: move the config path without resealing.
    (cursor / "mcp.json").rename(cursor / "mcp_moved.json")
    monkeypatch.setattr(build, "repo_root", lambda: root)
    with pytest.raises(SystemExit, match=r"AUTHORITY\.lock is stale|Dogfood"):
        build.check_dogfood_lock_freshness()
