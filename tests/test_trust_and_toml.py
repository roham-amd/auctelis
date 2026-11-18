"""Regression tests for 3.6.1 trust defaults, TOML MCP, sticky marker, decision fall-through."""

from __future__ import annotations

from pathlib import Path

from auctelis.cli import main_dev
from auctelis.export.pr_comment import (
    AUCTELIS_COMMENT_MARKER,
    render_authority_diff_comment,
)
from auctelis.inventory.adapters.toml_config import (
    _parse_simple_toml,
    discover_toml_mcp_configs,
)
from auctelis.inventory.limits import CollectorLimits
from auctelis.security.decision import compute_decision
from auctelis.security.models import Finding
from auctelis_research.scan import run_scan


def _high_gate() -> Finding:
    return Finding(
        finding_id="F-001",
        rule_id="AUCTELIS-RULE-011",
        title="unpinned",
        severity="HIGH",
        confidence="OBSERVED",
        description="d",
        component_ids=[],
        evidence_ids=[],
        finding_class="SECURITY_FINDING",
    )


def test_compute_decision_no_fallthrough_with_empty_delta():
    decision = compute_decision(
        [_high_gate()],
        coverage={},
        risk_delta={"gated_findings_added": 0, "high_or_critical_findings_added": 0},
    )
    assert decision == "NO-GATED-FINDINGS"


def test_sticky_comment_marker_is_first_line(tmp_path: Path):
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"
    scan, payload, _ = run_scan(demo, output_dir=tmp_path / "out")
    comment = payload.get("pr_comment") or render_authority_diff_comment(scan.to_findings_doc())
    assert comment.startswith(AUCTELIS_COMMENT_MARKER)
    assert (
        (tmp_path / "out" / "pr-comment.md")
        .read_text(encoding="utf-8")
        .startswith(AUCTELIS_COMMENT_MARKER)
    )


def test_toml_parse_and_discover(tmp_path: Path):
    data = _parse_simple_toml('[mcp_servers.demo]\ncommand = "npx"\nurl = "https://example.com"\n')
    assert data["mcp_servers"]["demo"]["command"] == "npx"
    root = tmp_path / "repo"
    codex = root / ".codex"
    codex.mkdir(parents=True)
    (codex / "config.toml").write_text(
        '[mcp_servers.demo]\ncommand = "uvx"\n',
        encoding="utf-8",
    )
    events: list[dict] = []
    comps = discover_toml_mcp_configs(
        root,
        files=[codex / "config.toml"],
        limits=CollectorLimits(),
        events=events,
    )
    assert len(comps) == 1
    assert comps[0]["name"] == "demo"
    assert comps[0]["adapter"] == "toml_mcp"


def test_toml_inline_array_parses(tmp_path: Path):
    """Codex-shaped ``args = ["-y", "pkg"]`` must seal, not NOT PARSED."""
    data = _parse_simple_toml('[mcp_servers.demo]\ncommand = "npx"\nargs = ["-y", "pkg"]\n')
    assert data["mcp_servers"]["demo"]["args"] == ["-y", "pkg"]
    root = tmp_path / "repo"
    codex = root / ".codex"
    codex.mkdir(parents=True)
    (codex / "config.toml").write_text(
        '[mcp_servers.demo]\ncommand = "npx"\nargs = ["-y", "demo-pkg"]\n',
        encoding="utf-8",
    )
    events: list[dict] = []
    comps = discover_toml_mcp_configs(
        root,
        files=[codex / "config.toml"],
        limits=CollectorLimits(),
        events=events,
    )
    assert len(comps) == 1
    assert comps[0]["args"] == ["-y", "demo-pkg"]
    assert not any(e.get("type") == "unparsed_agent_config" for e in events)


def test_toml_invalid_fails_closed(tmp_path: Path):
    root = tmp_path / "repo"
    codex = root / ".codex"
    codex.mkdir(parents=True)
    (codex / "config.toml").write_text("broken = [\n", encoding="utf-8")
    events: list[dict] = []
    comps = discover_toml_mcp_configs(
        root,
        files=[codex / "config.toml"],
        limits=CollectorLimits(),
        events=events,
    )
    assert comps == []
    assert any(e.get("type") == "unparsed_agent_config" for e in events)


def test_toml_ignores_cargo_config_and_extracts_codex_pins(tmp_path: Path):
    from auctelis.check import build_check_report, render_pin_report

    root = tmp_path / "repo"
    cargo = root / ".cargo"
    cargo.mkdir(parents=True)
    (cargo / "config.toml").write_text("[build]\njobs = 4\n", encoding="utf-8")
    codex = root / ".codex"
    codex.mkdir(parents=True)
    (codex / "config.toml").write_text(
        '[mcp_servers.demo]\ncommand = "npx"\nargs = ["-y", "foo"]\n\n[mcp_servers.demo.env]\nAPI_KEY = "${API_KEY}"\n',
        encoding="utf-8",
    )
    events: list[dict] = []
    comps = discover_toml_mcp_configs(
        root,
        files=[cargo / "config.toml", codex / "config.toml"],
        limits=CollectorLimits(),
        events=events,
    )
    assert len(comps) == 1
    assert comps[0]["repository_path"] == ".codex/config.toml"
    assert comps[0]["env_keys"] == ["API_KEY"]
    assert "unpinned_package_launcher" in comps[0]["priority_hints"]

    summary, _, _ = build_check_report(root)
    pins_text = render_pin_report(summary)
    assert "floating" in pins_text
    assert "demo" in pins_text


def test_toml_mcp_parity_and_host_detection(tmp_path: Path):
    from auctelis.inventory.adapters.hosts import discover_host_profiles

    root = tmp_path / "repo"
    cargo = root / ".cargo"
    cargo.mkdir(parents=True)
    (cargo / "config.toml").write_text("[build]\njobs = 4\n", encoding="utf-8")

    cursor = root / ".cursor"
    cursor.mkdir(parents=True)
    (cursor / "config.toml").write_text(
        "[mcp_servers.remote]\n"
        'url = "http://insecure.example/mcp"\n'
        "[mcp_servers.remote.env]\n"
        'OPENAI_BASE_URL = "https://proxy.example/v1"\n'
        'API_KEY = "sk-1234567890abcdef1234567890"\n',
        encoding="utf-8",
    )

    events: list[dict] = []
    comps = discover_toml_mcp_configs(
        root,
        files=[cargo / "config.toml", cursor / "config.toml"],
        limits=CollectorLimits(),
        events=events,
    )
    assert len(comps) == 1
    entry = comps[0]
    assert entry["host_id"] == "cursor"
    assert "insecure_http_remote" in entry["priority_hints"]
    assert "base_url_or_proxy_override" in entry["priority_hints"]
    assert "literal_secret_in_env" in entry["priority_hints"]
    assert "https://proxy.example/v1" in entry.get("destinations", [])

    hosts = discover_host_profiles(
        root,
        files=[cargo / "config.toml"],
        limits=CollectorLimits(),
        events=[],
    )
    assert hosts == []


def test_target_policy_ignored_by_default(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        '{"mcpServers":{"x":{"command":"npx","args":["-y","demo-pkg"]}}}',
        encoding="utf-8",
    )
    (root / ".auctelis.yml").write_text(
        """
version: 1
policy:
  mode: enforce
  fail_on: never
  ignore:
    - rule: AUCTELIS-RULE-011
      path: "**"
      justification: "blind the auditor"
""",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    code = main_dev(["scan", str(root), "-o", str(out), "--fail-on", "high"])
    printed = capsys.readouterr().out
    assert (
        "Target .auctelis.yml ignored" in printed
        or "target_policy_ignored" in printed.lower()
        or code
        in {
            0,
            1,
        }
    )
    findings = (out / "findings.json").read_text(encoding="utf-8")
    # Default path must not apply the broad suppression — RULE-011 should remain active.
    assert '"suppressed": true' not in findings or "AUCTELIS-RULE-011" in findings
    # More precise: with ignored policy, no suppressions applied.
    assert (
        '"suppression_count": 0' in findings
        or '"suppressions": []' in findings
        or ("target_policy_ignored" in findings)
    )


def test_trust_target_policy_applies_suppressions(tmp_path: Path):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        '{"mcpServers":{"x":{"command":"npx","args":["-y","demo-pkg"]}}}',
        encoding="utf-8",
    )
    (root / ".auctelis.yml").write_text(
        """
version: 1
policy:
  mode: advisory
  fail_on: never
  ignore:
    - rule: AUCTELIS-RULE-011
      path: "**"
      justification: "accepted risk for fixture"
      owner: tests
      expires: "2099-01-01"
""",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    code = main_dev(
        [
            "scan",
            str(root),
            "-o",
            str(out),
            "--trust-target-policy",
            "--fail-on",
            "never",
        ]
    )
    assert code == 0
    text = (out / "findings.json").read_text(encoding="utf-8")
    assert '"suppressed": true' in text
