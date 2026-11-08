"""Tests for authdiff 90-day surfaces + radical-alt MVPs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from authdiff.artifact_vet import parse_artifact_spec
from authdiff.atlas.crawl import DEMO_SEEDS, run_crawl
from authdiff.broker import load_authority_lock, run_brokered
from authdiff.lsp_stub import validate_authority_doc
from authdiff.mcp_snapshot import (
    diff_tool_locks,
    snapshot_execute,
    snapshot_from_file,
    tools_from_list_payload,
)
from authdiff.process_env import scrub_env
from authdiff.security.decision import compute_decision, decision_sentences
from authdiff.security.scan import run_scan


def test_parse_artifact_spec():
    assert parse_artifact_spec("npm:lodash@4.17.21") == ("npm", "lodash", "4.17.21")
    assert parse_artifact_spec("pypi:requests==2.32.0") == ("pypi", "requests", "2.32.0")
    assert parse_artifact_spec("@scope/pkg")[0] == "npm"


def test_scrub_env_drops_secrets(monkeypatch):
    monkeypatch.setenv("PATH", "/bin")
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LOG_LEVEL", "info")
    env = scrub_env(extra={"AUTHDIFF_BROKER": "1"})
    assert "PATH" in env
    assert "GITHUB_TOKEN" not in env
    assert "OPENAI_API_KEY" not in env
    assert "LOG_LEVEL" not in env
    assert env.get("AUTHDIFF_SCRUBBED_ENV") == "1"
    assert env.get("AUTHDIFF_BROKER") == "1"


def test_snapshot_from_tools_list(tmp_path: Path):
    payload = {
        "tools": [
            {
                "name": "read_file",
                "description": "Read a file from disk",
                "inputSchema": {"properties": {"path": {"type": "string"}}},
            }
        ]
    }
    path = tmp_path / "tools.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    doc = snapshot_from_file(path)
    assert doc["ok"] is True
    assert doc["tool_count"] == 1
    assert doc["tools"][0]["description_sha256"].startswith("sha256:")
    assert "read_file" in doc["authority_lock_fragment"]["mcp_tools"]


def test_snapshot_execute_rejects_metacharacters():
    with pytest.raises(ValueError, match="metacharacters"):
        snapshot_execute(["bash|evil"])


def test_snapshot_execute_non_json(tmp_path: Path):
    script = tmp_path / "say.py"
    script.write_text("print('not-json')\n", encoding="utf-8")
    doc = snapshot_execute([sys.executable, str(script)])
    assert doc["ok"] is False
    assert "not JSON" in str(doc.get("error") or "")


def test_snapshot_execute_ok_json(tmp_path: Path):
    script = tmp_path / "tools_out.py"
    script.write_text(
        "import json; print(json.dumps({'tools':[{'name':'t','description':'d'}]}))\n",
        encoding="utf-8",
    )
    doc = snapshot_execute([sys.executable, str(script)])
    assert doc["ok"] is True
    assert doc["tool_count"] == 1
    assert doc["network_enforced"] is False


def test_diff_tool_locks_detects_rug_pull():
    base = {"a": "sha256:" + "a" * 64}
    head = {"a": "sha256:" + "b" * 64, "c": "sha256:" + "c" * 64}
    diff = diff_tool_locks(base, head)
    assert diff["rug_pull_suspect"] is True
    assert diff["tools_added"] == ["c"]
    assert diff["description_hash_changed"] == ["a"]


def test_load_authority_lock_json(tmp_path: Path):
    path = tmp_path / "AUTHORITY.lock.json"
    path.write_text(
        json.dumps({"version": 1, "mcp_tools": {"x": "sha256:" + "ab" * 32}}),
        encoding="utf-8",
    )
    lock = load_authority_lock(path)
    assert lock["mcp_tools"]["x"].startswith("sha256:")


def test_run_brokered_echo(tmp_path: Path, capsys):
    code = run_brokered([sys.executable, "-c", "print(42)"])
    assert code == 0
    out = capsys.readouterr().out
    assert "authdiff.run" in out
    assert "limitations" in out


def test_run_brokered_rejects_metacharacters():
    with pytest.raises(ValueError, match="metacharacters"):
        run_brokered(["cmd|bad"])


def test_lsp_validate_lock(tmp_path: Path):
    lock = {
        "version": 1,
        "mcp_tools": {"read_file": "sha256:" + "ab" * 32},
    }
    path = tmp_path / "AUTHORITY.lock.json"
    path.write_text(json.dumps(lock), encoding="utf-8")
    diags = validate_authority_doc(path)
    assert diags == []


def test_lsp_validate_invalid_digest(tmp_path: Path):
    lock = {"version": 1, "mcp_tools": {"read_file": "not-a-digest"}}
    path = tmp_path / "AUTHORITY.lock.json"
    path.write_text(json.dumps(lock), encoding="utf-8")
    diags = validate_authority_doc(path)
    assert any(d.get("severity") == "error" for d in diags)


def test_atlas_crawl_demo(tmp_path: Path):
    summary = run_crawl(demo_seed=True, out_dir=tmp_path / "ledger-run")
    assert summary["seed_count"] == len(DEMO_SEEDS)
    assert summary["scanned_ok"] >= 1
    assert (tmp_path / "ledger-run" / "crawl-summary.json").is_file()


def test_attack_replay_sessionstart(tmp_path: Path):
    root = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "attack-replay"
        / "01-sessionstart-curl-env"
    )
    scan, _p, _c = run_scan(root, output_dir=tmp_path / "out")
    fired = {f.rule_id for f in scan.findings}
    assert "AUTHDIFF-RULE-015" in fired or "AUTHDIFF-RULE-004" in fired
    assert compute_decision(scan.findings, coverage=scan.coverage) in {"BLOCK", "REVIEW"}


def test_decision_sentences_no_gated_with_coverage_gaps():
    lines = decision_sentences(
        "NO-GATED-FINDINGS",
        [],
        coverage={
            "component_counts_by_maturity": {
                "SUPPORTED": 1,
                "PARTIAL": 3,
                "MANUAL_ONLY": 1,
                "UNSUPPORTED": 0,
            }
        },
    )
    assert any("NO-GATED-FINDINGS" in line for line in lines)
    assert any("could not" in line.lower() or "coverage" in line.lower() for line in lines)


def test_tools_from_list_payload_nested():
    tools = tools_from_list_payload({"result": {"tools": [{"name": "x", "description": "y"}]}})
    assert len(tools) == 1
    assert tools[0].name == "x"
