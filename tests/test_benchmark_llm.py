from pathlib import Path

from authdiff.benchmark.llm_runner import run_llm_benchmark


def test_llm_validate_only():
    summary = run_llm_benchmark(validate_only=True)
    assert summary["mode"] == "validate_ground_truth_only"
    assert summary["failed"] == 0
    assert summary["passed"] >= 8
    assert summary["dataset_version"]
    assert summary["rubric_version"]


def test_llm_score_good_submissions():
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "benchmark"
        / "llm"
        / "submissions"
        / "sample-good"
    )
    summary = run_llm_benchmark(submissions=root)
    assert summary["failed"] == 0
    assert summary["mode"] == "score_submissions"
    sample = summary["results"][0]["scores"]
    assert "detection_quality" in sample
    assert "evidence_quality" in sample
    assert "severity_quality" in sample
    assert "unsupported_claims" in sample


def test_llm_score_detects_hallucination():
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "benchmark"
        / "llm"
        / "submissions"
        / "sample-hallucinated"
    )
    summary = run_llm_benchmark(submissions=root)
    assert summary["failed"] >= 1
    scores = summary["results"][0]["scores"]
    assert scores["hallucinated_claims"] >= 1 or scores["false_positives"] >= 1


def test_llm_pilot_multi_agent():
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "benchmark"
        / "llm"
        / "submissions"
        / "pilots"
    )
    summary = run_llm_benchmark(submissions=root)
    assert "agent-careful" in summary["agents_scored"]
    assert "agent-aggressive" in summary["agents_scored"]
    careful = [r for r in summary["results"] if r["agent"] == "agent-careful"]
    aggressive = [r for r in summary["results"] if r["agent"] == "agent-aggressive"]
    assert careful and all(r["ok"] for r in careful)
    assert aggressive and any(not r["ok"] for r in aggressive)
