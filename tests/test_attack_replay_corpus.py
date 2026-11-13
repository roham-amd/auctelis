"""Week 4: parametrized attack-replay expected signals."""

from __future__ import annotations

from pathlib import Path

import pytest

from auctelis.security.decision import compute_decision
from auctelis.security.scan import run_scan

_REPLAY = Path(__file__).resolve().parents[1] / "examples" / "attack-replay"

_CASES = [
    pytest.param(
        "01-sessionstart-curl-env",
        {"AUCTELIS-RULE-015", "AUCTELIS-RULE-004"},
        None,
        id="01-sessionstart-curl-env",
    ),
    pytest.param(
        "02-enable-all-project-mcp",
        {"AUCTELIS-RULE-018", "AUCTELIS-RULE-017"},
        None,
        id="02-enable-all-project-mcp",
    ),
    pytest.param(
        "03-base-url-hijack",
        {"AUCTELIS-RULE-019"},
        None,
        id="03-base-url-hijack",
    ),
    pytest.param(
        "04-mcp-bash-pipe",
        {"AUCTELIS-RULE-015"},
        None,
        id="04-mcp-bash-pipe",
    ),
    pytest.param(
        "05-skill-sudo-pipe",
        {"AUCTELIS-RULE-015"},
        None,
        id="05-skill-sudo-pipe",
    ),
    pytest.param(
        "06-hidden-html-comment",
        {"AUCTELIS-RULE-010"},
        None,
        id="06-hidden-html-comment",
    ),
    pytest.param(
        "07-jsonc-padded-mcp",
        set(),
        "flex_unparsed_or_rule011",
        id="07-jsonc-padded-mcp",
    ),
    pytest.param(
        "08-pr-target-agent",
        {"AUCTELIS-RULE-016"},
        None,
        id="08-pr-target-agent",
    ),
    pytest.param(
        "09-literal-mcp-secret",
        {"AUCTELIS-RULE-012"},
        None,
        id="09-literal-mcp-secret",
    ),
    pytest.param(
        "10-unpinned-npx",
        {"AUCTELIS-RULE-011"},
        None,
        id="10-unpinned-npx",
    ),
]


@pytest.mark.parametrize("case_dir,expected_rules,special", _CASES)
def test_attack_replay_expected_signals(
    tmp_path: Path, case_dir: str, expected_rules: set[str], special: str | None
):
    root = _REPLAY / case_dir
    assert root.is_dir(), case_dir
    scan, _payload, _code = run_scan(root, output_dir=tmp_path / case_dir, fail_on="never")
    fired = {f.rule_id for f in scan.findings}
    if special == "flex_unparsed_or_rule011":
        unparsed = int(scan.coverage.get("unparsed_agent_config_count") or 0)
        assert (
            "AUCTELIS-RULE-011" in fired
            or unparsed > 0
            or compute_decision(scan.findings, coverage=scan.coverage) == "REVIEW"
        ), (fired, unparsed, scan.parser_events)
        return
    assert expected_rules & fired, f"{case_dir}: expected one of {expected_rules}, got {fired}"
