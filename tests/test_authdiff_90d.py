"""Tests for advanced product surfaces (snapshot, broker, decisions)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from authdiff.artifact_vet import parse_artifact_spec
from authdiff.broker import run_brokered
from authdiff.lock_io import load_authority_lock
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
    assert "read_file" in doc["authority_lock_fragment"]["mcp_tools"]


def test_diff_tool_locks_detects_change():
    a = {"read": "sha256:" + "ab" * 32}
    b = {"read": "sha256:" + "cd" * 32, "write": "sha256:" + "ef" * 32}
    delta = diff_tool_locks(a, b)
    assert "write" in delta["tools_added"]
    assert "read" in delta["description_hash_changed"]
    assert delta["rug_pull_suspect"] is True


def test_snapshot_execute_python_json(tmp_path: Path):
    script = tmp_path / "emit.py"
    script.write_text(
        "import json; print(json.dumps({'tools':[{'name':'t','description':'d'}]}))",
        encoding="utf-8",
    )
    doc = snapshot_execute([sys.executable, str(script)], allow_network=False)
    assert doc.get("ok") is True
    assert doc.get("tool_count", 0) >= 1


def test_broker_lock_roundtrip(tmp_path: Path):
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
