"""Week 4: HIGH/CRITICAL gated findings must not use INFERRED_HINT alone."""

from __future__ import annotations

from pathlib import Path

import pytest
from auctelis.security.gating import is_high_gate_finding
from auctelis.security.scan import run_scan

_REPLAY = Path(__file__).resolve().parents[1] / "examples" / "attack-replay"
_DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"


@pytest.mark.parametrize("root", [_DEMO, *_REPLAY.iterdir()])
def test_high_critical_not_inferred_hint_only(tmp_path: Path, root: Path):
    if not root.is_dir():
        pytest.skip("not a directory")
    scan, _payload, _code = run_scan(
        root, output_dir=tmp_path / root.name, fail_on="never"
    )
    bad = [
        f
        for f in scan.findings
        if is_high_gate_finding(f)
        and (f.evidence_strength or "") == "INFERRED_HINT"
        and (f.finding_class or "") == "SECURITY_FINDING"
    ]
    assert not bad, [(f.rule_id, f.finding_id, f.evidence_strength) for f in bad]
