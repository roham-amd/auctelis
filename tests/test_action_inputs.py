"""AUCT-006 — Action inputs cannot neutralize the gate."""

from __future__ import annotations

from pathlib import Path


def _action_text() -> str:
    return (
        Path(__file__).resolve().parents[1] / ".github" / "actions" / "auctelis-gate" / "action.yml"
    ).read_text(encoding="utf-8")


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


def test_deprecated_inputs_warn():
    text = _action_text()
    assert "Warn on deprecated gate-neutralizing inputs" in text
    assert "inputs.baseline is deprecated" in text


def test_strict_defaults_on_when_locked():
    text = _action_text()
    strict_block = text.split("strict-ruleset:", 1)[1][:800]
    assert 'default: ""' in strict_block
    assert "locked=true default" in text
    assert "AUCTELIS_LOCKED" in text


def test_first_run_prefers_watching_on_workflow_add():
    text = _action_text()
    assert "Workflow install PR and no sticky comment yet" in text
    # Prefer FIRST_RUN even when a growth pr-comment.md already exists.
    assert 'cp "$FIRST_RUN" "$COMMENT"' in text
    assert "workflow_added" in text


def test_research_baseline_skipped_unless_annotate():
    text = _action_text()
    assert "Research baseline skipped (annotate=false)" in text
    assert "Extract base-ref AUTHORITY.lock (tree-truth)" in text
    # Coverage report is research-only (needs inventory.json from annotate).
    block = text.split("Report incomplete coverage", 1)[1].split("Note SARIF path", 1)[0]
    assert "inputs.annotate == 'true'" in block


def test_org_reusable_workflow_pins_current_release():
    from auctelis.versioning import product_version

    root = Path(__file__).resolve().parents[1]
    path = root / "docs" / "auctelis-org-reusable.yml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "workflow_call" in text
    assert f"auctelis-gate@v{product_version()}" in text
