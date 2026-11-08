from pathlib import Path

from authdiff.benchmark.governance import verify_dataset_integrity
from authdiff.benchmark.llm_runner import _load_dataset_manifest, run_llm_benchmark
from authdiff.benchmark.report import build_evaluation_report


def test_dataset_governance_checksums():
    summary = verify_dataset_integrity(_load_dataset_manifest())
    assert summary["ok"] is True
    assert summary["case_count_actual"] >= 8


def test_llm_validate_includes_integrity_and_splits():
    summary = run_llm_benchmark(validate_only=True, split="public")
    assert summary["failed"] == 0
    assert summary["split"] == "public"
    assert summary["case_count"] == 4
    assert summary["dataset_integrity"]["ok"] is True
    assert summary["evaluation_pin"]["dataset_version"]


def test_evaluation_report_is_transparent():
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "benchmark"
        / "llm"
        / "submissions"
        / "pilots"
    )
    report = build_evaluation_report(submissions=root, split="public")
    assert report["kind"] == "agentsecbench_evaluation_report"
    assert report["dataset_integrity"]["ok"] is True
    assert "per_agent" in report and "per_case" in report
    assert "overall" in report
    assert report["sample_size"]["cases_in_split"] == 4
    assert "leaderboard" not in report["kind"]
    assert any(
        "leaderboard" in lim.lower() or "small" in lim.lower() for lim in report["limitations"]
    )
