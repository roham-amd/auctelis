"""Week 4: Action-style lock / base-lock / ci init flow harness."""

from __future__ import annotations

import json
from pathlib import Path

from authdiff.cli import main
from authdiff.policy import load_policy


def test_flow_mcp_addition_base_lock_then_accept(tmp_path: Path):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}),
        encoding="utf-8",
    )
    assert main(["lock", str(root)]) == 0
    base = tmp_path / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")

    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "a": {"command": "node", "args": ["a.js"]},
                    "b": {"command": "node", "args": ["b.js"]},
                }
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out-add"
    assert (
        main(
            [
                "scan",
                str(root),
                "-o",
                str(out),
                "--fail-on",
                "never",
                "--base-lock",
                str(base),
            ]
        )
        == 1
    )

    assert main(["lock", str(root), "--accept-gated", "--approval", "@sec"]) == 0
    out_ok = tmp_path / "out-ok"
    fresh_base = root / "AUTHORITY.lock"
    assert (
        main(
            [
                "scan",
                str(root),
                "-o",
                str(out_ok),
                "--fail-on",
                "never",
                "--base-lock",
                str(fresh_base),
            ]
        )
        == 0
    )


def test_ci_init_policy_ignore_empty_list(tmp_path: Path):
    root = tmp_path / "fresh"
    root.mkdir()
    assert main(["ci", "init", str(root), "--owner", "@sec-owners"]) == 0
    policy = load_policy(root / ".authdiff.yml")
    assert policy.suppressions == []
