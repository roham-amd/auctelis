"""AUCT-001..008 — day-zero diff, honest verdict, quiet NONE, reach/trust/pins."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from auctelis.authority_card import pin_report, reach_snapshot, record_card
from auctelis.check import build_check_report, render_check, render_pin_report
from auctelis.cli import main
from auctelis.diff_base import run_diff_base
from auctelis.export.pr_comment import render_authority_diff_comment
from auctelis.gate import render_gate_report, run_gate
from auctelis.lock_io import compute_lock_hash
from auctelis.reach_tiers import (
    TIER_COMMENT,
    TIER_FAIL,
    load_trusted_hosts,
    record_reach_tier,
)


def test_validated_http_url_rejects_non_http_schemes():
    from auctelis.textutil import validated_http_url

    assert validated_http_url("https://api.github.com/repos/x/y") == (
        "https://api.github.com/repos/x/y"
    )
    for bad in ("file:///etc/passwd", "javascript:alert(1)", "ftp://example.com", "/local"):
        try:
            validated_http_url(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted non-http URL: {bad}")


def test_api_probe_rejects_non_http_base():
    from auctelis.gate import _api_get_json

    assert _api_get_json("file:///etc/passwd", token="t") == (None, 0)


def test_empty_authority_lock_is_fresh_and_schema_shaped():
    from auctelis.lock_io import empty_authority_lock

    first = empty_authority_lock()
    second = empty_authority_lock()
    assert first == second
    assert first is not second
    first["records"].append({"name": "x"})
    assert second["records"] == []
    assert first["version"] == 1 and first["mcp_tools"] == {}


def _mcp(root: Path, servers: dict) -> None:
    cfg = root / ".cursor"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": servers}, indent=2) + "\n",
        encoding="utf-8",
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")


def _empty_lock() -> dict:
    lock = {"version": 1, "records": [], "mcp_tools": {}}
    lock["lock_hash"] = compute_lock_hash(lock)
    return lock


def _write_base(tmp_path: Path, lock: dict | None = None) -> Path:
    base = tmp_path / "base.lock"
    base.write_text(json.dumps(lock or _empty_lock()), encoding="utf-8")
    return base


# --- AUCT-001 day-zero diff -------------------------------------------------


def test_diff_base_without_lock_is_baseline_needed(tmp_path: Path):
    root = tmp_path / "repo"
    _init_repo(root)
    _mcp(root, {"linear": {"command": "npx", "args": ["-y", "@linear/mcp"]}})
    _git(root, "add", ".")
    _git(root, "commit", "-m", "no lock")

    text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert code == 0
    assert payload["verdict"] == "BASELINE_NEEDED"
    assert payload["baseline_state"] == "absent"
    assert payload["label"] == "NONE"
    assert "BASELINE_NEEDED" in text
    assert 'mcp "linear"' in text
    assert "absolute head reach" in text
    assert "auctelis lock --update" in text
    assert "FAIL_CLOSED" not in text


def test_diff_base_absent_and_no_head_authority_is_pass(tmp_path: Path):
    root = tmp_path / "repo"
    _init_repo(root)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "empty")

    _text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert code == 0
    assert payload["baseline_state"] == "absent"
    assert payload["verdict"] == "PASS"
    assert payload["label"] == "NONE"


def test_diff_base_invalid_ref_still_fails_closed(tmp_path: Path):
    root = tmp_path / "repo"
    _init_repo(root)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base")

    text, payload, code = run_diff_base(root, base_ref="does-not-exist")
    assert code == 2
    assert payload["verdict"] == "FAIL_CLOSED"
    assert payload["baseline_state"] == "invalid_ref"
    assert "unknown git ref" in text


def test_diff_base_with_lock_does_not_say_absolute_head_scan(tmp_path: Path):
    from auctelis.authority_lock import write_authority_lock

    root = tmp_path / "repo"
    _init_repo(root)
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    write_authority_lock(root)
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base")
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )

    _text, payload, code = run_diff_base(root, base_ref="HEAD")
    assert code == 1
    assert payload["baseline_state"] == "present"
    assert payload["label"] == "GROWTH"
    assert "absolute head" not in payload["comment"].lower()


# --- AUCT-002 honest verdict ------------------------------------------------


def test_comment_only_growth_is_needs_review_not_pass(tmp_path: Path):
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
    report, code = run_gate(
        root,
        base_lock=_write_base(tmp_path),
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    assert code == 0
    assert report["label"] == "GROWTH"
    assert report["verdict"] == "NEEDS_REVIEW"
    assert report["mode"] == "comment-only"
    assert "NEEDS_REVIEW" in render_gate_report(report)
    assert "advisory; check not failing" in render_gate_report(report)


def test_comment_only_no_change_is_pass_none(tmp_path: Path):
    from auctelis.authority_lock import build_authority_lock

    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base = _write_base(tmp_path, build_authority_lock(root))
    report, code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    assert code == 0
    assert report["label"] == "NONE"
    assert report["verdict"] == "PASS"
    assert "No material authority growth" in render_gate_report(report)


def test_comment_only_growth_never_says_no_action():
    delta = {
        "summary": {"additions": 1},
        "changes": {
            "added": [
                {
                    "kind": "MCP Server Registration",
                    "name": "linear",
                    "path": ".cursor/mcp.json",
                    "capabilities": ["access_network", "invoke_tools"],
                    "destinations": ["mcp.linear.app"],
                    "env_keys": ["API_TOKEN"],
                    "evidence_strength": "LITERAL_CONFIG",
                }
            ],
            "changed": [],
            "removed": [],
        },
        "lines": [],
    }
    comment = render_authority_diff_comment(
        {"findings": [], "coverage": {}},
        lock_delta=delta,
        verdict="NEEDS_REVIEW",
        mode="comment-only",
    )
    assert "`NEEDS_REVIEW`" in comment
    assert "CODEOWNERS review required before merge" in comment
    assert "No action beyond reviewing Unknowns" not in comment
    # Secret names are shown (markdown-escaped), never values.
    assert "env:" in comment and "API\\_TOKEN" in comment


def test_comment_default_never_pre_approves_growth_with_owners():
    delta = {
        "summary": {"additions": 1},
        "changes": {
            "added": [
                {
                    "kind": "MCP Server Registration",
                    "name": "linear",
                    "path": ".cursor/mcp.json",
                    "capabilities": ["access_network"],
                    "destinations": ["mcp.linear.app"],
                    "evidence_strength": "LITERAL_CONFIG",
                }
            ],
            "changed": [],
            "removed": [],
        },
        "lines": [],
    }
    comment = render_authority_diff_comment(
        {"findings": [], "coverage": {}},
        lock_delta=delta,
        needs_approval_from=["@security"],
    )
    assert "**Verdict:** `NEEDS_REVIEW`" in comment
    assert "**Verdict:** `PASS`" not in comment
    assert "Needs approval from:" in comment


def test_comment_only_reduction_stays_pass(tmp_path: Path):
    from auctelis.authority_lock import build_authority_lock

    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base = _write_base(tmp_path, build_authority_lock(root))
    # Remove the server: head authority is empty.
    (root / ".cursor" / "mcp.json").unlink()
    report, code = run_gate(
        root,
        base_lock=base,
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    assert code == 0
    assert report["label"] == "REDUCTION"
    assert report["verdict"] == "PASS"


# --- AUCT-003 quiet on NONE -------------------------------------------------


def _gate(tmp_path: Path, monkeypatch, out: Path, root: Path, *extra: str) -> int:
    monkeypatch.setenv("AUCTELIS_OUTPUT_DIR", str(out))
    return main(
        [
            "gate",
            str(root),
            "--base-lock",
            str(_write_base(tmp_path, _empty_lock())),
            "--skip-ruleset-check",
            "--comment-only",
            *extra,
        ]
    )


def test_comment_policy_auto_skips_none(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("x\n", encoding="utf-8")
    out = tmp_path / "out"
    assert _gate(tmp_path, monkeypatch, out, root) == 0
    assert (out / "comment-skip.txt").is_file()
    assert not (out / "pr-comment.md").exists()
    assert "PASS" in (out / "gate-report.txt").read_text(encoding="utf-8")


def test_comment_policy_auto_comments_growth(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"linear": {"command": "npx", "args": ["-y", "@linear/mcp"]}})
    out = tmp_path / "out"
    assert _gate(tmp_path, monkeypatch, out, root) == 0
    assert (out / "pr-comment.md").is_file()
    assert not (out / "comment-skip.txt").exists()
    assert "NEEDS_REVIEW" in (out / "pr-comment.md").read_text(encoding="utf-8")


def test_comment_policy_always_posts_none(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("x\n", encoding="utf-8")
    out = tmp_path / "out"
    assert _gate(tmp_path, monkeypatch, out, root, "--comment-policy", "always") == 0
    assert (out / "pr-comment.md").is_file()
    assert not (out / "comment-skip.txt").exists()


def test_action_has_comment_on_none_escape_hatch():
    action = (
        Path(__file__).resolve().parents[1] / ".github" / "actions" / "auctelis-gate" / "action.yml"
    )
    text = action.read_text(encoding="utf-8")
    assert "comment-on-none:" in text
    assert "--comment-policy always" in text
    assert "--comment-policy auto" in text
    assert "comment-skip.txt" in text


# --- Reach report / show the why -------------------------------------------


def test_check_first_run_is_ranked_reach_report(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
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
    report, cards, _scan = build_check_report(root)
    assert report["first_run"] is True
    reach = report["reach"]
    assert reach["total"] >= 2
    assert reach["tier_counts"]["tier2"] >= 1
    assert len(cards) <= 5
    assert 'mcp "linear"' in cards[0]  # highest tier first
    text = render_check(report, cards)
    assert "Reach:" in text
    assert "env: API_TOKEN" in text
    assert "publisher NOT VERIFIED" in text


def test_check_top_zero_hides_cards(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"linear": {"command": "npx", "args": ["-y", "@linear/mcp"]}})
    report, cards, _scan = build_check_report(root, top=0)
    assert report["first_run"] is True
    assert cards == []
    assert "Reach:" in render_check(report, cards)


def test_check_locked_still_shows_reach_cards(tmp_path: Path):
    from auctelis.authority_lock import write_authority_lock

    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"linear": {"command": "npx", "args": ["-y", "@linear/mcp"]}})
    write_authority_lock(root)
    report, cards, _scan = build_check_report(root)
    assert report["verdict"] == "LOCKED"
    assert cards
    assert 'mcp "linear"' in cards[0]
    assert "Reach:" in render_check(report, cards)


def test_added_card_shows_env_names_and_tier_reason():
    card = record_card(
        {
            "kind": "MCP Server Registration",
            "name": "linear",
            "path": ".cursor/mcp.json",
            "destinations": ["mcp.linear.app"],
            "capabilities": ["access_network", "invoke_tools"],
            "env_keys": ["API_TOKEN"],
            "pin_state": "floating",
            "launcher": "npx",
            "evidence_strength": "LITERAL_CONFIG",
        }
    )
    assert "env: API_TOKEN" in card
    assert "tier 2" in card
    assert "secrets" in card


def test_reach_snapshot_ranks_fail_tier_first():
    records = [
        {
            "kind": "Rule / instruction file",
            "name": "docs",
            "path": "AGENTS.md",
            "capabilities": ["modify_agent_instructions"],
            "destinations": ["docs.python.org"],
            "evidence_strength": "INFERRED_HINT",
        },
        {
            "kind": "MCP Server Registration",
            "name": "danger",
            "path": ".mcp.json",
            "capabilities": ["execute", "access_secrets"],
            "destinations": ["evil.example"],
            "evidence_strength": "LITERAL_CONFIG",
        },
    ]
    snap = reach_snapshot(records, limit=5)
    assert snap["top"][0]["name"] == "danger"
    assert snap["tier_counts"]["tier2"] == 1


# --- Trusted destinations ---------------------------------------------------


def _benign_mcp(name: str = "docs", host: str = "mcp.linear.app") -> dict:
    rec = {
        "kind": "MCP Server Registration",
        "name": name,
        "path": ".cursor/mcp.json",
        "capabilities": ["access_network", "invoke_tools"],
        "destinations": [host],
        "pin_state": "n/a",
        "launcher": "",
        "evidence_strength": "LITERAL_CONFIG",
    }
    return rec


def test_trusted_host_lowers_benign_network_to_comment_tier():
    rec = _benign_mcp()
    assert record_reach_tier(rec) >= TIER_FAIL
    assert record_reach_tier(rec, trusted_hosts={"mcp.linear.app"}) == TIER_COMMENT


def test_trusted_host_never_hides_secrets_or_execute():
    rec = {**_benign_mcp(), "env_keys": ["API_TOKEN"]}
    assert record_reach_tier(rec, trusted_hosts={"mcp.linear.app"}) >= TIER_FAIL


def test_trusted_host_stops_benign_mcp_growth_from_paging(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    cfg = root / ".cursor"
    cfg.mkdir()
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": {"docs": {"url": "https://mcp.linear.app/sse"}}}),
        encoding="utf-8",
    )
    trusted = root / ".auctelis"
    trusted.mkdir()
    (trusted / "trusted-hosts").write_text("mcp.linear.app\n", encoding="utf-8")
    owners = root / ".github"
    owners.mkdir()
    (owners / "CODEOWNERS").write_text(
        ".auctelis/trusted-hosts @sec\nAUTHORITY.lock @sec\n",
        encoding="utf-8",
    )

    report, code = run_gate(
        root,
        base_lock=_write_base(tmp_path),
        check_ruleset=False,
        strict_ruleset=False,
        trust_head_codeowners=True,
    )
    assert code == 0
    assert report["label"] == "GROWTH"
    assert report["max_reach_tier"] == TIER_COMMENT
    assert report["needs_approval"] is False
    assert report["verdict"] == "PASS"
    assert report["trusted_hosts_ignored"] is False


def test_uncovered_trust_file_is_ignored(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    cfg = root / ".cursor"
    cfg.mkdir()
    (cfg / "mcp.json").write_text(
        json.dumps({"mcpServers": {"docs": {"url": "https://mcp.linear.app/sse"}}}),
        encoding="utf-8",
    )
    trusted = root / ".auctelis"
    trusted.mkdir()
    (trusted / "trusted-hosts").write_text("mcp.linear.app\n", encoding="utf-8")

    report, _code = run_gate(
        root,
        base_lock=_write_base(tmp_path),
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    assert report["trusted_hosts_ignored"] is True
    assert report["max_reach_tier"] >= TIER_FAIL
    assert "trusted-hosts" in str(report.get("error") or "")


def test_trust_file_rejects_tld_and_wildcard_entries(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".auctelis").mkdir(parents=True)
    (root / ".auctelis" / "trusted-hosts").write_text(
        "com\n*.example.com\nmcp.linear.app\nlocalhost\n",
        encoding="utf-8",
    )
    assert load_trusted_hosts(root) == {"mcp.linear.app", "localhost"}


def test_trust_cli_rejects_tld(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["trust", "com", "--repo", str(root)]) == 2
    assert "not a specific host" in capsys.readouterr().out


def test_trust_cli_writes_and_removes_hosts(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["trust", "https://mcp.linear.app/sse", "--repo", str(root)]) == 0
    path = root / ".auctelis" / "trusted-hosts"
    assert path.is_file()
    assert load_trusted_hosts(root) == {"mcp.linear.app"}
    assert main(["trust", "--repo", str(root), "--list"]) == 0
    assert "mcp.linear.app" in capsys.readouterr().out
    assert main(["trust", "mcp.linear.app", "--repo", str(root), "--remove"]) == 0
    assert load_trusted_hosts(root) == set()


def test_trust_init_writes_starter_list(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["trust", "--repo", str(root), "--init"]) == 0
    assert "api.github.com" in load_trusted_hosts(root)


# --- MCP pin doctor --------------------------------------------------------


def test_pin_doctor_reports_unpinned_npx(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"linear": {"command": "npx", "args": ["-y", "@linear/mcp"]}})
    report, _cards, _scan = build_check_report(root)
    pins = report["pins"]
    assert pins["unpinned"] == 1
    assert pins["items"][0]["name"] == "linear"
    assert "npx" in pins["items"][0]["suggestion"]
    text = render_pin_report(report)
    assert "Unpinned MCP servers" in text
    assert "pin the package" in text
    assert "unpinned" in render_check(report, _cards)


def test_pin_doctor_quiet_when_pinned(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _mcp(root, {"linear": {"command": "npx", "args": ["-y", "@linear/mcp@1.2.3"]}})
    report, _cards, _scan = build_check_report(root)
    assert report["pins"]["unpinned"] == 0
    assert "No unpinned MCP servers" in render_pin_report(report)


def test_pin_report_suggestion_for_docker():
    pins = pin_report(
        [
            {
                "kind": "MCP Server Registration",
                "name": "container",
                "launcher": "docker",
                "pin_state": "floating",
            }
        ]
    )
    assert "sha256" in pins["items"][0]["suggestion"]


# --- AUCT-003 evidence-honest tiers ----------------------------------------


def _skill(name: str) -> dict:
    return {
        "kind": "Skill",
        "name": name,
        "path": f"skills/{name}/SKILL.md",
        "capabilities": [
            "access_secrets",
            "modify_agent_instructions",
            "execute_commands",
        ],
        "destinations": ["example.com"],
        "env_keys": [],
        "launcher": "",
        "evidence_strength": "INFERRED_HINT",
    }


def test_inferred_prose_secrets_is_comment_tier_not_fail():
    from auctelis.reach_tiers import reach_reason

    rec = _skill("docs-helper")
    assert record_reach_tier(rec) == TIER_COMMENT
    assert reach_reason(rec) == "inferred hint"
    card = record_card(rec)
    assert "tier 2" not in card
    assert "tier 1 (inferred hint)" in card


def test_literal_secrets_keeps_fail_tier():
    rec = {**_skill("literal"), "evidence_strength": "LITERAL_CONFIG"}
    assert record_reach_tier(rec) >= TIER_FAIL


def test_inferred_with_literal_env_keys_keeps_fail_tier():
    rec = {**_skill("with-env"), "env_keys": ["API_TOKEN"]}
    assert record_reach_tier(rec) >= TIER_FAIL


def test_inferred_with_launcher_keeps_fail_tier():
    rec = {**_skill("with-launcher"), "launcher": "npx", "pin_state": "pinned"}
    assert record_reach_tier(rec) >= TIER_FAIL


def test_inferred_prose_expansion_never_fails():
    from auctelis.reach_tiers import expansion_reach_tier

    before = {
        "kind": "Skill",
        "capabilities": ["modify_agent_instructions"],
        "destinations": [],
        "evidence_strength": "INFERRED_HINT",
    }
    after = {
        "kind": "Skill",
        "capabilities": ["modify_agent_instructions", "access_secrets", "execute_commands"],
        "destinations": ["example.com"],
        "evidence_strength": "INFERRED_HINT",
    }
    assert expansion_reach_tier(before, after) < TIER_FAIL


def test_skill_prose_secrets_never_fail_tier_end_to_end(tmp_path: Path):
    """The dogfood failure mode: a SKILL.md that merely *mentions* secrets."""
    from auctelis.authority_lock import build_authority_lock

    root = tmp_path / "repo"
    skill = root / "skills" / "docs-helper"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: docs-helper\n---\n\n# helper\n\nRead secrets from https://example.com/docs.\n",
        encoding="utf-8",
    )
    head = build_authority_lock(root)
    records = [r for r in head["records"] if "SKILL.md" in str(r.get("path"))]
    assert records
    rec = records[0]
    assert rec["evidence_strength"] == "INFERRED_HINT"
    assert "access_secrets" in rec["capabilities"]
    assert record_reach_tier(rec) < TIER_FAIL

    report, code = run_gate(
        root,
        base_lock=_write_base(tmp_path),
        check_ruleset=False,
        strict_ruleset=False,
        comment_only=True,
        trust_head_codeowners=True,
    )
    assert code == 0
    assert report["label"] == "GROWTH"
    assert report["max_reach_tier"] == TIER_COMMENT
    assert report["needs_approval"] is False
