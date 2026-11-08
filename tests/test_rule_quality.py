from authdiff.rules_quality.runner import run_rule_quality


def test_rule_quality_pack_passes():
    summary = run_rule_quality()
    assert summary["failed"] == 0, summary
    assert summary["passed"] >= 26
