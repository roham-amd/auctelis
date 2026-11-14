from pathlib import Path

from auctelis.policy import apply_policy_defaults, load_policy
from auctelis.security.scan import run_scan

SAMPLE = """
version: 1
policy:
  mode: enforce
  fail_on: high
  output_dir: auctelis-out
  baseline: .auctelis/baseline.json
  require_review:
    - remote_mcp_endpoint
  ignore:
    - rule: AUCTELIS-RULE-002
      path: "**/*"
      justification: "Test suppression for fixture"
      owner: tests
      expires: "2099-01-01"
"""


def test_load_policy_simple_yaml(tmp_path: Path):
    path = tmp_path / ".auctelis.yml"
    path.write_text(SAMPLE, encoding="utf-8")
    policy = load_policy(path)
    assert policy.mode == "enforce"
    assert policy.fail_on == "high"
    assert policy.require_review == ["remote_mcp_endpoint"]
    assert len(policy.suppressions) == 1
    assert policy.suppressions[0].rule == "AUCTELIS-RULE-002"
    assert policy.suppressions[0].justification.startswith("Test suppression")


def test_apply_policy_defaults_cli_wins():
    path_policy = None
    assert (
        apply_policy_defaults(policy=path_policy, fail_on="high", fail_on_from_cli=True)
        == "high"
    )
    assert (
        apply_policy_defaults(
            policy=path_policy, fail_on="never", fail_on_from_cli=True
        )
        is None
    )


def test_suppression_filters_findings(tmp_path: Path):
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "corpus"
        / "fixtures"
        / "skill-to-mcp-path"
    )
    policy_path = tmp_path / ".auctelis.yml"
    policy_path.write_text(SAMPLE, encoding="utf-8")
    policy = load_policy(policy_path)
    out = tmp_path / "out"
    scan, payload, code = run_scan(root, output_dir=out, policy=policy, fail_on=None)
    assert code == 0
    # Suppressed findings stay in the artifact stream, marked suppressed=True.
    suppressed = [
        f for f in scan.findings if f.rule_id == "AUCTELIS-RULE-002" and f.suppressed
    ]
    assert suppressed
    assert not any(
        f.rule_id == "AUCTELIS-RULE-002" and not f.suppressed for f in scan.findings
    )
    assert payload.get("suppressions")
    assert (out / "suppressions.json").is_file()


def test_default_output_not_under_target(tmp_path: Path, monkeypatch):
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "corpus"
        / "fixtures"
        / "benign-skill-only"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    scan, payload, code = run_scan(root)
    assert code == 0
    out = Path(payload["output_dir"])
    assert out == (cwd / "auctelis-out").resolve()
    assert not (root / "auctelis-out").exists()
    assert scan.findings is not None
