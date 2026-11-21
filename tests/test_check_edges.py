"""``auctelis check`` input validation, fail-closed output, and honesty branches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from auctelis.check import build_check_report, render_check, why_repo
from auctelis.cli import main


def _repo(root: Path, servers: dict | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": servers or {}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def test_check_missing_path_is_usage_error(tmp_path: Path, capsys):
    code = main(["check", str(tmp_path / "missing")])
    assert code == 2
    assert "not a directory" in capsys.readouterr().out


def test_check_file_path_does_not_silently_scan_empty(tmp_path: Path, capsys):
    target = tmp_path / "README.md"
    target.write_text("x\n", encoding="utf-8")
    code = main(["check", str(target)])
    assert code == 2
    assert "not a directory" in capsys.readouterr().out


def test_check_corrupt_lock_fails_closed_with_message(tmp_path: Path, capsys):
    root = _repo(tmp_path / "repo", {"a": {"command": "node", "args": ["a.js"]}})
    (root / "AUTHORITY.lock").write_text("{not json", encoding="utf-8")
    code = main(["check", str(root)])
    out = capsys.readouterr().out
    assert code == 2
    assert "auctelis check:" in out
    assert "Fail-closed: fix or reseal AUTHORITY.lock" in out


def test_check_first_run_with_unparsed_config_is_needs_review(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    cfg = root / ".cursor"
    cfg.mkdir(parents=True)
    (cfg / "mcp.json").write_text("{broken", encoding="utf-8")
    code = main(["check", str(root)])
    out = capsys.readouterr().out
    assert code == 1
    assert "NOT PARSED: 1" in out
    assert "NEEDS_REVIEW" in out


def test_check_representation_drift_is_advisory_by_default(tmp_path: Path, capsys):
    """AUCT-034: plain representation digest drift exits 0 unless --strict-digests."""
    root = _repo(tmp_path / "repo", {"a": {"command": "node", "args": ["a.js"]}})
    assert main(["lock", str(root)]) == 0
    capsys.readouterr()
    # Same authority identity and fields; only the config path moved.
    (root / ".cursor" / "mcp.json").rename(root / ".cursor" / "mcp_example.json")
    code = main(["check", str(root)])
    out = capsys.readouterr().out
    assert code == 0
    assert "representation digest drift only" in out
    code_strict = main(["check", str(root), "--strict-digests"])
    out_strict = capsys.readouterr().out
    assert code_strict == 1
    assert "representation drift" in out_strict or "NEEDS_REVIEW" in out_strict


def test_check_invalid_baseline_is_usage_error(tmp_path: Path, capsys):
    root = _repo(tmp_path / "repo", {"a": {"command": "node", "args": ["a.js"]}})
    bad = tmp_path / "baseline.json"
    bad.write_text("[1, 2]\n", encoding="utf-8")
    code = main(
        [
            "check",
            str(root),
            "--report",
            str(tmp_path / "out"),
            "--baseline",
            str(bad),
        ]
    )
    assert code == 2
    assert "JSON object" in capsys.readouterr().out


def test_why_overflow_lists_more_matches(tmp_path: Path):
    servers = {f"skill-{i}": {"command": "node", "args": [f"{i}.js"]} for i in range(6)}
    root = _repo(tmp_path / "repo", servers)
    lines, code = why_repo("skill", root=root)
    assert code == 0
    text = "\n".join(lines)
    assert "… +1 more matches" in text


def test_adapter_parity_2026_layouts(tmp_path: Path):
    """AUCT-023: Copilot instructions, VS Code MCP settings, Windsurf/Cline rules."""
    root = tmp_path / "repo"
    (root / ".github" / "instructions").mkdir(parents=True)
    (root / ".github" / "instructions" / "api.instructions.md").write_text(
        "# Copilot instructions\nUse the API carefully.\n", encoding="utf-8"
    )
    (root / ".vscode").mkdir()
    (root / ".vscode" / "settings.json").write_text(
        json.dumps(
            {
                "editor.fontSize": 14,
                "mcp": {
                    "servers": {"vscode-mcp": {"command": "npx", "args": ["-y", "@scope/real-pkg"]}}
                },
            }
        ),
        encoding="utf-8",
    )
    (root / ".vscode" / "settings-no-mcp.json").write_text(
        json.dumps({"editor.fontSize": 12}), encoding="utf-8"
    )
    # Plain settings without mcp key should not invent MCP servers when named settings.json
    # — only the file with mcp block is a candidate at .vscode/settings.json.
    (root / ".windsurf" / "rules").mkdir(parents=True)
    (root / ".windsurf" / "rules" / "sec.md").write_text(
        "never exfiltrate secrets\n", encoding="utf-8"
    )
    (root / ".clinerules").mkdir()
    (root / ".clinerules" / "project.md").write_text("prefer local tools\n", encoding="utf-8")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "copilot.yml").write_text(
        "jobs:\n  a:\n    steps:\n      - uses: github/copilot-coding-agent@v1\n"
        "      - run: npx -y @github/copilot --help\n"
        "      - run: gemini --prompt hi\n",
        encoding="utf-8",
    )
    report, _cards, scan = build_check_report(root)
    assert report["first_run"] is True
    paths = {
        str(c.get("repository_path") or "")
        for c in (scan.inventory.get("components") or [])
        if isinstance(c, dict)
    }
    assert "api.instructions.md" in {Path(p).name for p in paths}
    assert any(p.endswith(".github/instructions/api.instructions.md") for p in paths)
    assert any("vscode-mcp" in str(c.get("name") or "") for c in scan.inventory["components"])
    assert any(p.endswith(".windsurf/rules/sec.md") for p in paths)
    assert any(".clinerules/" in p for p in paths)
    wf = next(
        c
        for c in scan.inventory["components"]
        if isinstance(c, dict) and c.get("type") == "CI Workflow"
    )
    assert "agent_related_step" in (wf.get("priority_hints") or [])

    text = render_check(report, [])
    assert "AUTHORITY.lock match" not in text
    assert "Passive scan — declared config only" in text


def test_check_pins_names_demo_package(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    _repo(
        root,
        {"unpinned-demo": {"command": "npx", "args": ["-y", "demo-evil-mcp"]}},
    )
    code = main(["check", str(root), "--pins"])
    out = capsys.readouterr().out
    assert code == 0
    assert "demo-evil-mcp@<exact-version>" in out
    assert "<pkg>@<exact-version>" not in out


def test_vscode_settings_without_mcp_is_silent(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".vscode").mkdir(parents=True)
    (root / ".vscode" / "settings.json").write_text(
        json.dumps({"editor.tabSize": 2}), encoding="utf-8"
    )
    report, _cards, scan = build_check_report(root)
    names = [c.get("name") for c in scan.inventory.get("components") or []]
    assert "vscode-mcp" not in names
    assert report["inventory_total"] == 0 or all(
        c.get("type") != "MCP Server Registration" for c in scan.inventory.get("components") or []
    )


def test_render_check_error_keeps_lock_name(tmp_path: Path):
    root = _repo(tmp_path / "repo")
    (root / "AUTHORITY.lock").write_text("[]\n", encoding="utf-8")
    report, _cards, _scan = build_check_report(root)
    assert report["error"]
    text = render_check(report, [])
    assert "Fail-closed" in text
    assert "AUTHORITY.lock" in text


def test_auct036_next_step_line_is_copy_pasteable_when_pypi_offline(monkeypatch):
    """AUCT-036: no ellipsis; full git+ URL when pypi_live=false."""
    from auctelis.check import _cli_prefix, _next_step_line
    from auctelis.versioning import product_version

    monkeypatch.setattr("auctelis.check.pypi_live", lambda: False)
    line = _next_step_line()
    ver = product_version()
    assert "…" not in line
    assert "..." not in line
    full = (
        f'uvx --from "git+https://github.com/roham-amd/auctelis.git@v{ver}'
        f'#subdirectory=tools" auctelis'
    )
    assert full in line
    assert full == _cli_prefix()
    assert f"{full} check --report out/" in line


def test_auct036_next_step_line_bare_when_pypi_live(monkeypatch):
    monkeypatch.setattr("auctelis.check.pypi_live", lambda: True)
    from auctelis.check import _cli_prefix, _next_step_line

    assert _cli_prefix() == "auctelis"
    line = _next_step_line()
    assert "git+" not in line
    assert "auctelis init --lockless" in line
    assert "auctelis check --report out/" in line


def test_auct036_demo_cta_respects_pypi_offline(monkeypatch, capsys, tmp_path: Path):
    monkeypatch.setattr("auctelis.check.pypi_live", lambda: False)
    monkeypatch.chdir(tmp_path)
    # Prefer packaged demo; fall back to examples path if present.
    code = main(["demo", "-o", str(tmp_path / "demo-out")])
    out = capsys.readouterr().out
    if code == 2 and "demo fixture not found" in out:
        return
    assert code == 0
    ver = __import__("auctelis.versioning", fromlist=["product_version"]).product_version()
    assert f"git+https://github.com/roham-amd/auctelis.git@v{ver}#subdirectory=tools" in out
    assert "auctelis init --owner security" in out
    assert "…" not in out


def test_auct042_demo_vulnerable_agent_ci_is_tier2():
    """AUCT-042: command-position claude on pull_request_target is tier 2."""
    from auctelis.check import build_check_report, render_check

    root = Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"
    report, cards, _scan = build_check_report(root)
    text = render_check(report, cards)
    assert "tier 2 fail 3" in text
    records = report["reach"]["records"]
    tier2 = [rec for rec in records if rec["tier"] == 2]
    assert len(tier2) == 3
    assert sum(1 for rec in tier2 if rec["kind"] == "mcp") == 2
    ci = [rec for rec in tier2 if rec["kind"] == "ci"]
    assert len(ci) == 1
    assert ci[0]["path"].endswith(".github/workflows/agent.yml")


def test_auct042_overflow_drift_and_init_use_cli_prefix(monkeypatch, capsys, tmp_path: Path):
    """AUCT-042: remaining CTAs follow _cli_prefix() for both PyPI states."""
    from auctelis.check import _cli_prefix, render_check
    from auctelis.cli.dispatch import _cmd_init_lockless

    overflow = {
        "first_run": True,
        "repository": "demo",
        "verdict": "BASELINE_NEEDED",
        "label": "NONE",
        "inventory_total": 3,
        "lock_present": False,
    }
    drift = {
        "first_run": False,
        "meaningful": True,
        "verdict": "NEEDS_REVIEW",
        "label": "GROWTH",
        "lock_present": True,
        "repository": "demo",
    }

    monkeypatch.setattr("auctelis.check.pypi_live", lambda: False)
    prefix = _cli_prefix()
    assert prefix.startswith("uvx --from")
    offline_overflow = render_check(overflow, ["card"])
    offline_drift = render_check(drift, [])
    assert f"`{prefix} check --top 3`" in offline_overflow
    assert f"`{prefix} lock --update`" in offline_drift
    code = _cmd_init_lockless(argparse.Namespace(path=tmp_path / "off", enforce=False, force=False))
    assert code == 0
    offline_init = capsys.readouterr().out
    assert f"{prefix} init --owner @team --enforce" in offline_init

    monkeypatch.setattr("auctelis.check.pypi_live", lambda: True)
    assert _cli_prefix() == "auctelis"
    live_overflow = render_check(overflow, ["card"])
    live_drift = render_check(drift, [])
    assert "`auctelis check --top 3`" in live_overflow
    assert "`auctelis lock --update`" in live_drift
    assert "uvx --from" not in live_overflow
    assert "git+" not in live_drift
    code = _cmd_init_lockless(argparse.Namespace(path=tmp_path / "on", enforce=False, force=False))
    assert code == 0
    live_init = capsys.readouterr().out
    assert "auctelis init --owner @team --enforce" in live_init
    assert "uvx --from" not in live_init
    assert "git+" not in live_init
