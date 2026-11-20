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


def test_legacy_baseline_does_not_skip_auth_diff():
    text = _action_text()
    # The auth_diff step must not gate on inputs.baseline == ''.
    marker = "Extract base-ref AUTHORITY.lock (tree-truth)"
    assert marker in text
    block = text.split(marker, 1)[1].split("shell: bash", 1)[0]
    assert "inputs.baseline == ''" not in block
    assert "inputs.authority-diff == 'true'" in block


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


def test_strict_defaults_on_when_locked():
    text = _action_text()
    strict_block = text.split("strict-ruleset:", 1)[1][:800]
    assert 'default: ""' in strict_block
    assert "locked=true default" in text
    assert "AUCTELIS_LOCKED" in text


def test_first_run_prefers_watching_on_workflow_add():
    text = _action_text()
    assert "Workflow install PR and no sticky comment yet" in text or "installation check" in text
    assert 'cp "$FIRST_RUN" "$COMMENT"' in text
    assert "workflow_added" in text
    assert "prepending Watching banner" in text


def test_tree_truth_base_extract_without_research():
    text = _action_text()
    assert "Extract base-ref AUTHORITY.lock (tree-truth)" in text
    assert "Research baseline skipped" not in text
    assert "Report incomplete coverage" not in text
    assert "Note SARIF path" not in text


def test_org_reusable_workflow_pins_current_release():
    from auctelis.versioning import product_version

    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "auctelis-org-reusable.yml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "workflow_call" in text
    assert f"roham-amd/auctelis@v{product_version()}" in text
    assert "annotate" not in text


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
