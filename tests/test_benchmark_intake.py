from pathlib import Path

import pytest

from authdiff.benchmark.intake import (
    build_submitter_package,
    intake_submission_dir,
    list_external_intakes,
    verify_evaluation_contract,
)
from authdiff.jsonio import write_json


def test_evaluation_contract_frozen():
    summary = verify_evaluation_contract()
    assert summary["ok"] is True
    assert summary["contract_id"] == "AgentSecBench-LLM-EVAL-0.3.0"
    assert summary["pins"]["dataset_version"] == "0.3.0"


def test_submitter_package_omits_ground_truth(tmp_path: Path):
    out = tmp_path / "pkg"
    result = build_submitter_package(out)
    assert result["ok"] is True
    assert result["case_count"] >= 8
    card = (out / "LLM-004.task.json").read_text(encoding="utf-8")
    assert "ground_truth" not in card
    package = (out / "PACKAGE.json").read_text(encoding="utf-8")
    assert (
        '"includes_ground_truth": false' in package
        or '"includes_ground_truth":false' in package.replace(" ", "")
    )


def test_intake_rejects_missing_execution(tmp_path: Path):
    src = tmp_path / "bad"
    src.mkdir()
    write_json(
        src / "LLM-001.json",
        {"case_id": "LLM-001", "model": "x", "findings": []},
    )
    record = intake_submission_dir(src, agent_id="tester", provenance="external", dry_run=True)
    assert record["ok"] is False
    assert any("execution" in e for e in record["files"][0]["errors"])


def test_intake_accepts_valid_and_preserves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from authdiff.benchmark import intake as intake_mod

    vault = tmp_path / "vault"
    monkeypatch.setattr(intake_mod, "vault_root", lambda: vault)

    src = tmp_path / "good"
    src.mkdir()
    write_json(
        src / "LLM-001.json",
        {
            "case_id": "LLM-001",
            "model": "ext/model-a",
            "agent_id": "independent-agent",
            "findings": [],
            "execution": {
                "produced_at_utc": "2026-11-04T12:00:00Z",
                "fixture_ref": "tests/benchmark/fixtures/x",
                "dataset_version_claimed": "0.3.0",
            },
        },
    )
    record = intake_submission_dir(src, agent_id="independent-agent", provenance="external")
    assert record["ok"] is True
    assert record["is_external_evidence"] is True
    run_dir = vault / "received" / record["run_id"]
    assert (run_dir / "LLM-001.json").is_file()
    assert (run_dir / "INTAKE.json").is_file()
    assert record["files"][0]["sha256"]

    listed = list_external_intakes()
    # list_external_intakes reads the real vault; with monkeypatched vault_root on
    # intake only, re-check via the written registry under our temp vault.
    registry = (vault / "REGISTRY.jsonl").read_text(encoding="utf-8")
    assert "independent-agent" in registry
    assert listed is not None


def test_template_not_labeled_external_evidence():
    """Templates under submissions/templates must not be treated as vault external evidence."""
    templates = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "benchmark"
        / "llm"
        / "submissions"
        / "templates"
    )
    assert templates.is_dir()
    listed = list_external_intakes()
    assert listed["valid_external_intakes"] == 0
    assert "example-agent" not in str(listed.get("external_run_ids"))


def test_intake_rejects_oversized_file(tmp_path: Path):
    from authdiff.benchmark import intake as intake_mod

    src = tmp_path / "big"
    src.mkdir()
    huge = src / "LLM-001.json"
    # Exceed MAX_SUBMISSION_FILE_BYTES without being valid JSON of interest.
    huge.write_bytes(b"x" * (intake_mod.MAX_SUBMISSION_FILE_BYTES + 1))
    record = intake_submission_dir(src, agent_id="tester", provenance="external", dry_run=True)
    assert record["ok"] is False
    assert any("exceeds" in e for e in record["files"][0]["errors"])


def test_intake_rejects_too_many_findings(tmp_path: Path):
    from authdiff.benchmark import intake as intake_mod

    src = tmp_path / "many"
    src.mkdir()
    write_json(
        src / "LLM-001.json",
        {
            "case_id": "LLM-001",
            "model": "x",
            "findings": [
                {"title": f"f{i}", "severity": "LOW", "status": "POTENTIAL"}
                for i in range(intake_mod.MAX_FINDINGS_PER_FILE + 1)
            ],
            "execution": {
                "produced_at_utc": "2026-11-04T12:00:00Z",
                "fixture_ref": "x",
                "dataset_version_claimed": "0.3.0",
            },
        },
    )
    record = intake_submission_dir(src, agent_id="tester", provenance="external", dry_run=True)
    assert record["ok"] is False
    assert any("findings exceed" in e for e in record["files"][0]["errors"])


def test_collection_status_zeros_until_evidence():
    from authdiff.benchmark.intake import collection_status

    status = collection_status()
    assert status["funnel"]["valid_external_intakes"] == 0
    assert status["funnel"]["invitations"] == 0
    assert status["minimum_evidence_met"] is False
    assert status["collection_status"] == "open"


def test_submitter_package_includes_participation(tmp_path: Path):
    out = tmp_path / "pkg"
    result = build_submitter_package(out)
    assert result["ok"] is True
    assert (out / "PARTICIPATION.md").is_file()
    assert "ground_truth_findings" not in (out / "LLM-004.task.json").read_text(encoding="utf-8")
