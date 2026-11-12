"""Six scenario harness: add / expand / reduce / approved / policy / hollow.

Simulates the Action contract without GitHub: scan --base-lock stays advisory,
`authdiff gate` is the sole authority-growth verdict.
"""

from __future__ import annotations

import json
from pathlib import Path

from authdiff.cli import main
from authdiff.gate import run_gate


def _mcp(root: Path, servers: dict) -> None:
    path = root / ".cursor" / "mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


def _owners(root: Path, owner: str = "@sec-owners") -> None:
    gh = root / ".github"
    gh.mkdir(parents=True, exist_ok=True)
    (gh / "CODEOWNERS").write_text(
        f"AUTHORITY.lock {owner}\n.authdiff.yml {owner}\n", encoding="utf-8"
    )


def _lock_base(root: Path, tmp: Path) -> Path:
    assert main(["lock", str(root)]) == 0
    base = tmp / "base.lock"
    base.write_text((root / "AUTHORITY.lock").read_text(encoding="utf-8"), encoding="utf-8")
    return base


def _scan_base(root: Path, out: Path, base: Path) -> int:
    return main(
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


def test_scenario_add_needs_approval(tmp_path: Path):
    root = tmp_path / "add"
    _owners(root)
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base = _lock_base(root, tmp_path)
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    assert _scan_base(root, tmp_path / "out-add", base) == 0
    report, code = run_gate(root, base_lock=base)
    assert code == 1 and report["needs_approval"] is True


def test_scenario_expand_needs_approval(tmp_path: Path):
    root = tmp_path / "expand"
    _owners(root)
    _mcp(
        root,
        {"a": {"command": "node", "args": ["a.js"], "env": {}}},
    )
    base = _lock_base(root, tmp_path)
    _mcp(
        root,
        {
            "a": {
                "command": "node",
                "args": ["a.js"],
                "env": {"API_KEY": "x"},
            }
        },
    )
    assert _scan_base(root, tmp_path / "out-expand", base) == 0
    report, code = run_gate(root, base_lock=base)
    assert code == 1
    assert report["needs_approval"] is True or report["meaningful_authority_change"] is True


def test_scenario_reduce_does_not_need_approval(tmp_path: Path):
    root = tmp_path / "reduce"
    _owners(root)
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    base = _lock_base(root, tmp_path)
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    assert _scan_base(root, tmp_path / "out-reduce", base) == 0
    report, code = run_gate(root, base_lock=base)
    assert code == 0
    assert report["needs_approval"] is False


def test_scenario_approved_goes_green(tmp_path: Path):
    root = tmp_path / "approved"
    _owners(root, "@sec-owners")
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base = _lock_base(root, tmp_path)
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    assert _scan_base(root, tmp_path / "out-ok", base) == 0
    report, code = run_gate(root, base_lock=base, approved_by=["@sec-owners"])
    assert code == 0
    assert report["verdict"] == "PASS"


def test_scenario_team_owner_any_github_approval(tmp_path: Path):
    """Team CODEOWNERS: any APPROVED review counts, enforcement marked UNVERIFIED."""
    root = tmp_path / "team"
    _owners(root, "@org/security-owners")
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    base = _lock_base(root, tmp_path)
    _mcp(
        root,
        {
            "a": {"command": "node", "args": ["a.js"]},
            "b": {"command": "node", "args": ["b.js"]},
        },
    )
    assert run_gate(root, base_lock=base)[1] == 1
    report, code = run_gate(root, base_lock=base, approved_by=["@alice"])
    assert code == 0
    assert report.get("approval_enforcement") == "UNVERIFIED"


def test_scenario_hollow_lock_fails_closed(tmp_path: Path):
    root = tmp_path / "hollow"
    _owners(root)
    _mcp(root, {"a": {"command": "node", "args": ["a.js"]}})
    assert main(["lock", str(root)]) == 0
    hollow = tmp_path / "hollow.lock"
    hollow.write_text(
        json.dumps({"version": 1, "records": [], "lock_hash": "deadbeef", "mcp_tools": {}}),
        encoding="utf-8",
    )
    code = main(["gate", str(root), "--base-lock", str(hollow)])
    assert code in {1, 2}


def test_scenario_same_name_swap(tmp_path: Path):
    root = tmp_path / "swap"
    _owners(root)
    _mcp(root, {"svc": {"command": "npx", "args": ["-y", "pkg@1.0.0"]}})
    base = _lock_base(root, tmp_path)
    _mcp(root, {"svc": {"command": "npx", "args": ["-y", "evil@9.9.9"]}})
    assert _scan_base(root, tmp_path / "out-swap", base) == 0
    report, code = run_gate(root, base_lock=base)
    assert code == 1 and report["needs_approval"] is True
