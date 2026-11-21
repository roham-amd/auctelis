"""AUCT-002 — post once on first run, then stay quiet."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import write_authority_lock
from auctelis.cli import main
from auctelis.export.pr_comment import (
    AUCTELIS_COMMENT_MARKER,
    render_first_run_comment,
    render_gate_pr_comment,
)
from auctelis.gate import run_gate


def _mcp(root: Path, servers: dict) -> None:
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": servers}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_gate_report_carries_head_reach_snapshot(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(
        root,
        {
            "linear": {
                "command": "npx",
                "args": ["-y", "@linear/mcp"],
                "env": {"API_TOKEN": "x"},
            }
        },
    )
    base, _lock = write_authority_lock(root)
    report, _code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    reach = report["reach"]
    assert reach["total"] >= 1
    assert reach["tier_counts"]["tier2"] >= 1
    assert reach["top_cards"]


def test_quiet_gate_writes_first_run_comment(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base, _lock = write_authority_lock(root)
    out = tmp_path / "out"
    monkeypatch.setenv("AUCTELIS_OUTPUT_DIR", str(out))

    code = main(
        [
            "gate",
            str(root),
            "--base-lock",
            str(base),
            "--skip-ruleset-check",
            "--comment-only",
        ]
    )
    assert code == 0
    # Quiet-on-NONE still applies: no normal diff comment.
    assert not (out / "pr-comment.md").exists()
    assert (out / "comment-skip.txt").is_file()

    first_run = out / "comment-first-run.md"
    assert first_run.is_file()
    body = first_run.read_text(encoding="utf-8")
    assert AUCTELIS_COMMENT_MARKER in body
    assert "first run" in body
    assert "**Watching:**" in body
    assert "`PASS`" in body
    assert "No authority change" not in body.replace("did not change", "")
    # ≤12 visible lines, marker excluded.
    assert len([line for line in body.splitlines() if line]) <= 12


def test_first_run_renderer_never_says_pass_on_growth():
    body = render_first_run_comment(
        {
            "verdict": "NEEDS_REVIEW",
            "label": "GROWTH",
            "meaningful_authority_change": True,
            "reach": {
                "total": 3,
                "tier_counts": {"tier0": 0, "tier1": 1, "tier2": 2},
                "top_cards": ['+ mcp "linear" → mcp.linear.app · tier 2 (secrets)'],
            },
            "delta": {
                "summary": {"additions": 1, "mcp_tools_added": 0},
                "changes": {
                    "added": [
                        {
                            "kind": "MCP Server Registration",
                            "name": "linear",
                            "path": ".cursor/mcp.json",
                        }
                    ],
                    "changed": [],
                    "removed": [],
                },
            },
        }
    )
    assert "**Verdict:** `NEEDS_REVIEW`" in body
    assert "**Verdict:** `PASS`" not in body
    assert "linear" in body


def test_first_run_install_workflow_only_is_pass():
    body = render_first_run_comment(
        {
            "verdict": "NEEDS_REVIEW",
            "label": "GROWTH",
            "meaningful_authority_change": True,
            "unparsed": 0,
            "lock_tree_drift": False,
            "reach": {
                "total": 1,
                "tier_counts": {"tier0": 1, "tier1": 0, "tier2": 0},
                "top_cards": ['+ ci "auctelis"'],
            },
            "delta": {
                "summary": {
                    "additions": 1,
                    "mcp_tools_added": 0,
                    "mcp_tools_changed": 0,
                    "policy_changed": False,
                    "policy_added": False,
                },
                "changes": {
                    "added": [
                        {
                            "kind": "CI Workflow",
                            "name": "auctelis",
                            "path": ".github/workflows/auctelis.yml",
                        }
                    ],
                    "changed": [],
                    "removed": [],
                },
            },
        }
    )
    assert "**Verdict:** `PASS`" in body
    assert "**Watching:**" in body


def test_first_run_install_plus_mcp_shows_needs_review_and_card():
    body = render_first_run_comment(
        {
            "verdict": "NEEDS_REVIEW",
            "label": "GROWTH",
            "meaningful_authority_change": True,
            "unparsed": 0,
            "reach": {
                "total": 2,
                "tier_counts": {"tier0": 1, "tier1": 0, "tier2": 1},
                "top_cards": [
                    '+ mcp "smuggle" → tier 2 (secrets)',
                    '+ ci "auctelis"',
                ],
            },
            "delta": {
                "summary": {
                    "additions": 2,
                    "mcp_tools_added": 0,
                    "mcp_tools_changed": 0,
                    "policy_changed": False,
                    "policy_added": False,
                },
                "changes": {
                    "added": [
                        {
                            "kind": "CI Workflow",
                            "name": "auctelis",
                            "path": ".github/workflows/auctelis.yml",
                        },
                        {
                            "kind": "MCP Server Registration",
                            "name": "smuggle",
                            "path": ".cursor/mcp.json",
                            "env_keys": ["TOKEN"],
                            "capabilities": ["access_secrets"],
                            "evidence_strength": "LITERAL_CONFIG",
                        },
                    ],
                    "changed": [],
                    "removed": [],
                },
            },
        }
    )
    assert "**Verdict:** `NEEDS_REVIEW`" in body
    assert "smuggle" in body
    assert "**Watching:**" in body


def test_first_run_renderer_names_zero_reach_honestly():
    from auctelis.check import _cli_prefix

    body = render_first_run_comment(
        {
            "verdict": "PASS",
            "label": "NONE",
            "reach": {
                "total": 0,
                "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 0},
                "top": [],
            },
        }
    )
    assert "No agent configuration was discovered" in body
    assert f"`{_cli_prefix()} check`" in body
    assert "`auctelis check`" not in body or _cli_prefix() == "auctelis"


def test_auct046_watching_includes_pin_fix_within_budget():
    snippet = '"args": ["-y", "@linear/mcp@<exact-version>"]'
    body = render_first_run_comment(
        {
            "verdict": "PASS",
            "label": "NONE",
            "meaningful_authority_change": False,
            "lock_tree_drift": False,
            "unparsed": 0,
            "reach": {
                "total": 1,
                "tier_counts": {"tier0": 0, "tier1": 0, "tier2": 1},
                "top_cards": ['mcp "linear" · tier 2'],
            },
            "pins": {
                "total": 1,
                "unpinned": 1,
                "items": [
                    {
                        "name": "linear",
                        "path": ".cursor/mcp.json",
                        "config_snippet": snippet,
                    }
                ],
            },
        }
    )
    assert "**Pin fix:**" in body
    assert "@linear/mcp@<exact-version>" in body
    assert len([line for line in body.splitlines() if line]) <= 12


def test_action_posts_first_run_only_without_sticky():
    action = (
        Path(__file__).resolve().parents[1] / ".github" / "actions" / "auctelis-gate" / "action.yml"
    )
    text = action.read_text(encoding="utf-8")
    assert "comment-first-run.md" in text
    assert "FIRST_RUN" in text
    assert "existing_id" in text
    assert "workflow_added" in text
    assert ".github/workflows/auctelis*.y*ml" in text
    assert 'cp "$FIRST_RUN" "$COMMENT"' in text
    assert "prepending Watching banner" in text
    assert "auctelis-dev" not in text


def test_install_shaped_growth_still_writes_first_run(tmp_path: Path, monkeypatch):
    """Growth (e.g. new workflow CI record) must still emit comment-first-run.md."""
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base, _lock = write_authority_lock(root)
    # Add a second MCP → GROWTH vs sealed base.
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {
                "command": "npx",
                "args": ["-y", "@new/mcp"],
                "env": {"TOKEN": "x"},
            },
        },
    )
    out = tmp_path / "out"
    monkeypatch.setenv("AUCTELIS_OUTPUT_DIR", str(out))
    code = main(
        [
            "gate",
            str(root),
            "--base-lock",
            str(base),
            "--skip-ruleset-check",
            "--comment-only",
        ]
    )
    assert code == 0
    assert (out / "pr-comment.md").is_file()
    assert (out / "comment-first-run.md").is_file()
    assert "**Watching:**" in (out / "comment-first-run.md").read_text(encoding="utf-8")


def _empty_base_lock(tmp_path: Path) -> Path:
    from auctelis.lock_io import compute_lock_hash, empty_authority_lock

    lock = empty_authority_lock()
    lock["lock_hash"] = compute_lock_hash(lock)
    path = tmp_path / "empty-base.lock"
    path.write_text(json.dumps(lock), encoding="utf-8")
    return path


def _write_auctelis_workflow(root: Path, name: str = "auctelis.yml") -> None:
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / name).write_text(
        "name: auctelis\non: [pull_request]\njobs:\n  diff:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo\n",
        encoding="utf-8",
    )


def test_run_gate_workflow_only_install_is_pass_watching(tmp_path: Path):
    """AUCT-010: live run_gate() + changes key → clean Watching on workflow-only PR."""
    root = tmp_path / "repo"
    root.mkdir()
    _write_auctelis_workflow(root)
    report, _code = run_gate(
        root,
        base_lock=_empty_base_lock(tmp_path),
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    assert (report.get("delta") or {}).get("changes")
    assert "records" not in (report.get("delta") or {})
    body = render_first_run_comment(report)
    assert "**Verdict:** `PASS`" in body
    assert "**Watching:**" in body


def test_run_gate_workflow_plus_mcp_is_needs_review(tmp_path: Path):
    """AUCT-010: install PR that also adds MCP stays NEEDS_REVIEW with the MCP named."""
    root = tmp_path / "repo"
    root.mkdir()
    _write_auctelis_workflow(root)
    _mcp(
        root,
        {
            "smuggle": {
                "command": "npx",
                "args": ["-y", "@evil/mcp"],
                "env": {"TOKEN": "x"},
            }
        },
    )
    report, _code = run_gate(
        root,
        base_lock=_empty_base_lock(tmp_path),
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    body = render_first_run_comment(report)
    assert "**Verdict:** `NEEDS_REVIEW`" in body
    assert "smuggle" in body


def test_run_gate_init_policy_plus_workflow_is_pass_watching(tmp_path: Path):
    """AUCT-010: auctelis init (workflow + first .auctelis.yml) stays PASS Watching."""
    root = tmp_path / "repo"
    root.mkdir()
    _write_auctelis_workflow(root, name="auctelis-gate.yml")
    tmpl = Path(__file__).resolve().parents[1] / "tools" / "auctelis" / "templates"
    (root / ".auctelis.yml").write_text(
        (tmpl / "auctelis.yml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    report, _code = run_gate(
        root,
        base_lock=_empty_base_lock(tmp_path),
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    summary = (report.get("delta") or {}).get("summary") or {}
    assert summary.get("policy_added") is True
    assert summary.get("policy_changed") is True
    body = render_first_run_comment(report)
    assert "**Verdict:** `PASS`" in body
    assert "**Watching:**" in body


def test_check_first_run_footer_points_at_report_not_lock_only(tmp_path: Path):
    from auctelis.check import build_check_report, render_check
    from auctelis.versioning import product_version, pypi_live

    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    report, cards, _scan = build_check_report(root)
    text = render_check(report, cards)
    assert "check --report" in text
    assert "…" not in text
    if pypi_live():
        assert "auctelis init --lockless" in text
    else:
        ver = product_version()
        assert f"git+https://github.com/roham-amd/auctelis.git@v{ver}#subdirectory=tools" in text
        assert "init --lockless" in text
    # No dead template path: the CLI writes the workflow itself.
    assert "templates/" not in text
    assert "auctelis-diff.yml" not in text
    # Optional enforce still mentioned, but not as the sole next step.
    assert "Next: auctelis lock --update" not in text


def _pin_growth_report(package_stem: str, *, name: str = "linear") -> dict:
    return {
        "verdict": "NEEDS_REVIEW",
        "mode": "comment-only",
        "required_owners": ["@security"],
        "unparsed": 0,
        "coverage": {},
        "delta": {
            "summary": {
                "additions": 1,
                "expansions": 0,
                "reductions": 0,
                "meaningful_authority_change": True,
                "max_reach_tier": 2,
            },
            "changes": {
                "added": [
                    {
                        "kind": "MCP Server Registration",
                        "name": name,
                        "path": ".cursor/mcp.json",
                        "launcher": "npx",
                        "pin_state": "floating",
                        "package_stem": package_stem,
                        "capabilities": ["invoke_tools"],
                        "env_keys": [],
                        "evidence_strength": "LITERAL_CONFIG",
                    }
                ],
                "changed": [],
                "removed": [],
            },
            "lines": [f'+ mcp "{name}"'],
        },
    }


def _pin_line(body: str) -> str:
    return next(line for line in body.splitlines() if "**Pin fix:**" in line)


def test_auct038_gate_pr_comment_includes_pin_fix():
    """AUCT-040: Pin fix is the literal snippet, not a truncated escape."""
    import json

    from auctelis.authority_card import pin_config_snippet

    report = _pin_growth_report("demo-evil-mcp")
    body = render_gate_pr_comment(report)
    snippet = '"args": ["-y", "demo-evil-mcp@<exact-version>"]'
    assert pin_config_snippet(report["delta"]["changes"]["added"][0]) == snippet
    assert snippet in body
    pin = _pin_line(body)
    assert "\\[" not in pin
    assert "&lt;" not in pin
    assert json.loads("{" + snippet + "}")["args"] == ["-y", "demo-evil-mcp@<exact-version>"]
    assert body.count("\n") <= 22


def test_auct040_hostile_pin_stays_inside_the_code_span():
    """Backticks, links, mentions, and HTML cannot break out of the span."""
    from auctelis.authority_card import pin_config_snippet
    from auctelis.textutil import markdown_code_span

    payloads = (
        "evil`name",
        "x](http://evil.example)",
        "@user",
        "<img src=x onerror=alert(1)>",
    )
    for payload in payloads:
        report = _pin_growth_report(payload, name="server")
        record = report["delta"]["changes"]["added"][0]
        span = markdown_code_span(pin_config_snippet(record))
        assert span is not None
        body = render_gate_pr_comment(report)
        assert span in body
        outside = body.replace(span, "", 1)
        assert "](http://" not in outside
        assert "@user" not in outside
        assert "<img" not in outside
        assert "**Pin fix:**" in body


def test_auct040_newline_or_long_pin_is_omitted():
    """Over-budget and multiline snippets are dropped, not truncated."""
    newline = render_gate_pr_comment(_pin_growth_report("demo\nevil", name="server"))
    # json.dumps keeps the snippet on one line (escaped newline). A raw line
    # break must not appear inside the pin, and the long-name case below is
    # still omitted rather than truncated.
    pin = _pin_line(newline)
    assert "\\n" in pin
    assert "demo\nevil" not in pin

    long_name = "p" * 120
    body = render_gate_pr_comment(_pin_growth_report(long_name, name="server"))
    assert "**Pin fix:**" not in body
    assert long_name[:40] not in body
    assert "…" not in body
