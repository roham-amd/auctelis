from datetime import date
from pathlib import Path

from auctelis.policy import Suppression, load_policy
from auctelis.security.gating import compute_exit_code, is_gate_finding, is_high_gate_finding
from auctelis.security.models import Finding


def _finding(*, fclass: str, severity: str, evidence_ids: list[str] | None = None) -> Finding:
    return Finding(
        finding_id="F-001",
        rule_id="AUCTELIS-RULE-001",
        title="t",
        severity=severity,  # type: ignore[arg-type]
        confidence="POTENTIAL",
        description="d",
        component_ids=[],
        evidence_ids=list(evidence_ids) if evidence_ids is not None else ["E-001"],
        finding_class=fclass,  # type: ignore[arg-type]
    )


def test_capability_never_gates():
    f = _finding(fclass="CAPABILITY", severity="CRITICAL")
    assert not is_gate_finding(f)
    assert not is_high_gate_finding(f)
    assert compute_exit_code("any", findings=[f]) == 0
    assert compute_exit_code("high", findings=[f]) == 0


def test_exposure_without_evidence_ids_never_gates():
    bare = _finding(fclass="EXPOSURE", severity="HIGH", evidence_ids=[])
    assert not is_gate_finding(bare)
    assert compute_exit_code("any", findings=[bare]) == 0


def test_fail_on_any_uses_gated_delta_not_all_keys():
    exposure = _finding(fclass="EXPOSURE", severity="LOW")
    assert compute_exit_code("any", findings=[exposure]) == 1
    assert (
        compute_exit_code(
            "any",
            findings=[],
            risk_delta_summary={"gated_findings_added": 1, "findings_added": 5},
        )
        == 1
    )
    assert (
        compute_exit_code(
            "any",
            findings=[],
            risk_delta_summary={"gated_findings_added": 0, "findings_added": 5},
        )
        == 0
    )


def test_baseline_mode_no_fallthrough_to_legacy_findings():
    """With a risk delta, exit code ignores absolute head findings."""
    legacy_high = _finding(fclass="SECURITY_FINDING", severity="HIGH")
    assert (
        compute_exit_code(
            "high",
            findings=[legacy_high],
            risk_delta_summary={
                "gated_findings_added": 0,
                "high_or_critical_findings_added": 0,
            },
        )
        == 0
    )
    assert (
        compute_exit_code(
            "high",
            findings=[legacy_high],
            risk_delta_summary={
                "gated_findings_added": 1,
                "high_or_critical_findings_added": 1,
            },
        )
        == 1
    )


def test_suppression_expires(tmp_path: Path):
    path = tmp_path / ".auctelis.yml"
    path.write_text(
        """
version: 1
policy:
  mode: advisory
  ignore:
    - rule: AUCTELIS-RULE-002
      path: "**/*"
      justification: "expired fixture"
      owner: tests
      expires: "2020-01-01"
""",
        encoding="utf-8",
    )
    policy = load_policy(path)
    assert policy.suppressions[0].is_expired(today=date(2026, 1, 1))
    assert (
        policy.applies_to_finding(
            rule_id="AUCTELIS-RULE-002",
            evidence_paths=["x.json"],
            today=date(2026, 1, 1),
        )
        is None
    )
    assert (
        policy.applies_to_finding(
            rule_id="AUCTELIS-RULE-002",
            evidence_paths=["x.json"],
            today=date(2019, 1, 1),
        )
        is not None
    )


def test_example_policy_loads():
    root = Path(__file__).resolve().parents[1]
    policy = load_policy(root / "examples" / "auctelis.policy.example.yml")
    assert policy.mode == "enforce"
    assert policy.fail_on == "high"
    assert policy.suppressions
    assert isinstance(policy.suppressions[0], Suppression)
