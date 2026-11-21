"""AUCT-039 — PyPI cutover stays order-safe until the name is claimed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auctelis.versioning import product_version
from auctelis_devtools import build


def test_manifest_action_and_packaged_data_agree():
    root = Path(__file__).resolve().parents[1]
    canonical = json.loads(
        (root / "canonical" / "release-manifest.json").read_text(encoding="utf-8")
    )
    packaged = json.loads(
        (root / "tools" / "auctelis" / "data" / "release-manifest.json").read_text(encoding="utf-8")
    )
    assert packaged == canonical
    flag = "true" if canonical.get("pypi_live") else "false"
    root_action = (root / "action.yml").read_text(encoding="utf-8")
    sub_action = (root / ".github" / "actions" / "auctelis-gate" / "action.yml").read_text(
        encoding="utf-8"
    )
    assert root_action == sub_action
    assert f'AUCTELIS_PYPI_DEFAULT="{flag}"' in root_action
    notes = build.check_pypi_cutover_readiness()
    assert any("matches canonical" in note for note in notes)


def test_cutover_order_is_claim_flip_publish_probe_tag(capsys):
    build.check_pypi_cutover_readiness()
    out = capsys.readouterr().out
    assert (
        out.index("1. Claim")
        < out.index("2. Bump+flip")
        < out.index("3. Publish")
        < out.index("4. Live probe")
        < out.index("5. Tag")
    )


def test_next_step_line_is_bare_when_live(monkeypatch):
    monkeypatch.setattr("auctelis.check.pypi_live", lambda: True)
    from auctelis.check import _cli_prefix, _next_step_line

    assert _cli_prefix() == "auctelis"
    line = _next_step_line()
    assert "git+" not in line
    assert "uvx --from" not in line
    assert "auctelis init --lockless" in line
    assert "auctelis check --report out/" in line


def test_live_probe_raises_on_non_200(monkeypatch, tmp_path: Path):
    import urllib.error

    root = tmp_path / "repo"
    (root / "canonical").mkdir(parents=True)
    (root / "canonical" / "release-manifest.json").write_text(
        json.dumps({"pypi_live": False, "product_version": product_version()}),
        encoding="utf-8",
    )
    publish = root / ".github" / "workflows" / "publish-pypi.yml"
    publish.parent.mkdir(parents=True)
    publish.write_text(
        "permissions:\n  id-token: write\nenvironment: pypi\n"
        "steps:\n  - run: uv publish\n  - run: curl -fsS https://pypi.org/pypi/auctelis/json\n",
        encoding="utf-8",
    )
    (root / "tools").mkdir()
    (root / "tools" / "pyproject.toml").write_text(
        '[project.scripts]\nauctelis = "auctelis.cli:main"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "repo_root", lambda: root)
    monkeypatch.setattr(build, "check_wheel_omits_research", lambda: ["ok wheel"])

    def _raise(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            url="https://pypi.org/pypi/auctelis/0/json",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    with pytest.raises(SystemExit, match=r"HTTP 404"):
        build.check_pypi_cutover_readiness(live=True)


def test_packaged_manifest_drift_fails_cutover_check(monkeypatch, tmp_path: Path):
    root = tmp_path / "repo"
    (root / "canonical").mkdir(parents=True)
    canonical = {"pypi_live": False, "product_version": product_version()}
    (root / "canonical" / "release-manifest.json").write_text(
        json.dumps(canonical), encoding="utf-8"
    )
    data = root / "tools" / "auctelis" / "data"
    data.mkdir(parents=True)
    drifted = dict(canonical)
    drifted["pypi_live"] = True
    (data / "release-manifest.json").write_text(json.dumps(drifted), encoding="utf-8")
    publish = root / ".github" / "workflows" / "publish-pypi.yml"
    publish.parent.mkdir(parents=True)
    publish.write_text(
        "permissions:\n  id-token: write\nenvironment: pypi\n"
        "steps:\n  - run: uv publish\n  - run: curl -fsS https://pypi.org/pypi/auctelis/json\n",
        encoding="utf-8",
    )
    (root / "tools" / "pyproject.toml").write_text(
        '[project.scripts]\nauctelis = "auctelis.cli:main"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "repo_root", lambda: root)
    monkeypatch.setattr(build, "check_wheel_omits_research", lambda: ["ok wheel"])
    with pytest.raises(SystemExit, match=r"release-manifest\.json"):
        build.check_pypi_cutover_readiness()


def test_release_and_publish_workflows_encode_the_guards():
    root = Path(__file__).resolve().parents[1]
    release = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert 'gh release view "$TAG" --json assets' in release
    assert "-lt 6" in release
    publish = (root / ".github" / "workflows" / "publish-pypi.yml").read_text(encoding="utf-8")
    assert "pypi.org/pypi/auctelis" in publish
    assert "SECONDS + 600" in publish
    assert "pypi-check --live" in publish
