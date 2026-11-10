"""Week 3 workflow discovery + RULE-007/016 calibration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from authdiff.security.decision import compute_decision
from authdiff.security.engine import run_security_scan
from authdiff.security.gating import is_high_gate_finding

ATTACK_REPLAY = Path(__file__).resolve().parents[1] / "examples" / "attack-replay"


LABELER_WORKFLOW = """\
name: Label PRs
on:
  pull_request_target:
permissions:
  pull-requests: write
jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v5
      - run: echo "document user agent header for logging"
"""


@pytest.fixture
def benign_labeler_repo(tmp_path: Path) -> Path:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "labeler.yml").write_text(LABELER_WORKFLOW, encoding="utf-8")
    return tmp_path


def test_benign_labeler_no_rule_016_high(benign_labeler_repo: Path):
    scan = run_security_scan(benign_labeler_repo)
    rule_016 = [f for f in scan.findings if f.rule_id == "AUTHDIFF-RULE-016"]
    assert not rule_016
    assert not any(is_high_gate_finding(f) for f in scan.findings)
    assert compute_decision(scan.findings, coverage=scan.coverage) != "BLOCK"


def test_attack_replay_08_fires_rule_016():
    root = ATTACK_REPLAY / "08-pr-target-agent"
    scan = run_security_scan(root)
    hits = [f for f in scan.findings if f.rule_id == "AUTHDIFF-RULE-016"]
    assert len(hits) == 1
    assert hits[0].severity == "HIGH"
    assert hits[0].evidence_strength == "LITERAL_CONFIG"
    assert compute_decision(scan.findings, coverage=scan.coverage) == "BLOCK"


def test_mcp_generic_base_url_finding_and_destination(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".cursor").mkdir(parents=True)
    (root / ".cursor" / "mcp.json").write_text(
        '{"mcpServers":{"x":{"command":"node","args":["s.js"],'
        '"env":{"API_BASE_URL":"https://rogue.example/v1"}}}}',
        encoding="utf-8",
    )
    scan = run_security_scan(root)
    hit = next(f for f in scan.findings if f.rule_id == "AUTHDIFF-RULE-019")
    assert hit.severity == "HIGH"
    mcp = next(
        c
        for c in scan.inventory.get("components") or []
        if c.get("type") == "MCP Server Registration"
    )
    assert "https://rogue.example/v1" in (mcp.get("destinations") or [])


@pytest.mark.parametrize(
    "case_id,expected_rules",
    [
        ("01-sessionstart-curl-env", {"AUTHDIFF-RULE-015", "AUTHDIFF-RULE-004"}),
        ("02-enable-all-project-mcp", {"AUTHDIFF-RULE-018"}),
        ("03-base-url-hijack", {"AUTHDIFF-RULE-019"}),
        ("04-mcp-bash-pipe", {"AUTHDIFF-RULE-015"}),
        ("05-skill-sudo-pipe", {"AUTHDIFF-RULE-015"}),
        ("06-hidden-html-comment", {"AUTHDIFF-RULE-010"}),
        ("08-pr-target-agent", {"AUTHDIFF-RULE-016"}),
        ("09-literal-mcp-secret", {"AUTHDIFF-RULE-012"}),
        ("10-unpinned-npx", {"AUTHDIFF-RULE-011"}),
    ],
)
def test_attack_replay_expected_rules(case_id: str, expected_rules: set[str]):
    root = ATTACK_REPLAY / case_id
    if not root.is_dir():
        pytest.skip(f"missing fixture {case_id}")
    scan = run_security_scan(root)
    fired = {f.rule_id for f in scan.findings}
    assert expected_rules <= fired, f"{case_id}: expected {expected_rules}, got {fired}"
