"""AUCT-006 / AUCT-009 — Action inputs cannot neutralize the gate; lean 0.14 surface."""

from __future__ import annotations

from pathlib import Path


def _action_text() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "action.yml").read_text(encoding="utf-8")


def _subpath_action_text() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / ".github" / "actions" / "auctelis-gate" / "action.yml").read_text(
        encoding="utf-8"
    )


def test_mode_invalid_fails_loudly():
    text = _action_text()
    assert "Reject unsupported mode" in text
    assert "inputs.mode != 'scan'" in text
    assert "only mode=scan is valid" in text


def test_deprecated_research_inputs_removed():
    """AUCT-009: deprecated research inputs and auctelis-dev are gone."""
    text = _action_text()
    assert "Warn on deprecated gate-neutralizing inputs" not in text
    for banned in (
        "baseline-inventory:",
        "upload-sarif:",
        "annotate:",
        "fail-on:",
        "no-policy:",
        "auctelis-dev",
    ):
        # Inputs use "name:" form; also ban step invocations.
        assert banned not in text
    # Keep a bare `baseline:` from sneaking back as an input key (tree-truth
    # prose may still say "baseline" in comments — only the input form is banned).
    assert "\n  baseline:\n" not in text
    assert "\n  baseline-inventory:\n" not in text


def test_unused_policy_input_and_resolution_step_are_gone():
    """The gate diffs tree-truth policy hashes; it never consumed a resolved policy path."""
    text = _action_text()
    assert "\n  policy:\n" not in text
    assert "Resolve trusted policy path" not in text
    assert "trusted_policy.outputs" not in text
    assert "trusted-policy:" in text  # the edit guard remains


def test_root_action_has_marketplace_branding_and_version_input():
    text = _action_text()
    assert "branding:" in text
    assert "icon: shield" in text
    assert "auctelis-version:" in text
    assert "mode=pypi" in text
    sub = _subpath_action_text()
    for key in ("path:", "locked:", "auctelis-version:", "install-tools-from:"):
        assert key in text and key in sub


def test_auctelis_pypi_default_matches_release_manifest():
    import json
    import re

    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "canonical" / "release-manifest.json").read_text(encoding="utf-8")
    )
    expected = "true" if manifest.get("pypi_live") else "false"
    text = _action_text()
    match = re.search(r'AUCTELIS_PYPI_DEFAULT="(true|false)"', text)
    assert match is not None
    assert match.group(1) == expected
    assert f'AUCTELIS_PYPI_DEFAULT="{expected}"' in _subpath_action_text()
    # Auto PyPI on tagged refs is gated; explicit install-tools-from: pypi still works.
    assert 'AUCTELIS_PYPI_DEFAULT}" == "true"' in text


def test_action_runs_auctelis_diff_only():
    text = _action_text()
    assert "auctelis diff --base" in text
    assert "auctelis lock" not in text
    assert "auctelis gate" not in text
