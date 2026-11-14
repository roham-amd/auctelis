"""Release-hardening coverage: CLI surface, lock diff, maintainer entry."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.authority_lock import write_authority_lock
from auctelis.cli import main
from auctelis.cli.parser import build_parser


def test_diff_lock_cli(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    mcp = root / ".cursor"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "node", "args": ["a.js"]}}}),
        encoding="utf-8",
    )
    base_lock, _ = write_authority_lock(root, path=tmp_path / "base.lock")
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
    head_lock, _ = write_authority_lock(root, path=tmp_path / "head.lock")
    code = main(["diff", "lock", str(base_lock), str(head_lock)])
    assert code == 1
    out = capsys.readouterr().out
    assert "+" in out


def test_main_dev_exposes_build():
    args = build_parser(include_dev=True).parse_args(["lint", "--check-format"])
    assert args.command == "lint"
    assert "build" in build_parser(include_dev=True).format_help()


def test_product_main_rejects_build():
    try:
        main(["build", "all"])
        ok = True
    except SystemExit as exc:
        ok = exc.code == 0
    assert ok is False


def test_scan_full_flag(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".cursor").mkdir(parents=True)
    (root / ".cursor" / "mcp.json").write_text(
        '{"mcpServers":{"x":{"command":"npx","args":["-y","pkg"]}}}',
        encoding="utf-8",
    )
    out = tmp_path / "out"
    assert main(["scan", str(root), "-o", str(out), "--fail-on", "never"]) == 0
    short = (out / "scan-summary.txt").read_text(encoding="utf-8")
    assert "DECISION:" in short
    assert len(short.splitlines()) <= 15
    assert (
        main(
            ["scan", str(root), "-o", str(out / "full"), "--full", "--fail-on", "never"]
        )
        == 0
    )
    full = (out / "full" / "scan-summary-full.txt").read_text(encoding="utf-8")
    assert "AUTHORITY SURFACES" in full or "DECISION SUMMARY" in full
    # The short artifact stays short even after --full.
    short_after_full = (out / "full" / "scan-summary.txt").read_text(encoding="utf-8")
    assert len(short_after_full.splitlines()) <= 15
