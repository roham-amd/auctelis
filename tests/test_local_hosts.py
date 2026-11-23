"""AUCT-066: auctelis inspect --local read-only host-config audit."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.cli import main


def _file_set(root: Path) -> set[str]:
    return {str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()}


def test_local_hosts_flags_unpinned_and_base_url_without_writing_home(
    tmp_path: Path, capsys
) -> None:
    (tmp_path / ".cursor").mkdir(parents=True)
    (tmp_path / ".cursor" / "mcp.json").write_text(
        '{"mcpServers":{"x":{"command":"npx","args":["-y","demo-pkg"]}}}',
        encoding="utf-8",
    )
    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text(
        '{"env":{"ANTHROPIC_BASE_URL":"http://127.0.0.1:9/v1"}}',
        encoding="utf-8",
    )
    before = _file_set(tmp_path)

    code = main(["inspect", "--local", "--home", str(tmp_path), "--json", "--offline"])
    captured = capsys.readouterr()
    assert code == 1, f"exit {code}, stderr={captured.err!r}"
    assert _file_set(tmp_path) == before

    doc = json.loads(captured.out)
    rule_ids = {str(rf.get("rule_id") or "") for rf in doc.get("red_flags") or []}
    assert "AUCTELIS-RULE-011" in rule_ids
    assert "AUCTELIS-RULE-019" in rule_ids


def test_local_flag_conflicts_exit_2(tmp_path: Path, capsys) -> None:
    code = main(["inspect", "--local", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 2
    assert "auctelis inspect: --local cannot be combined with TARGET." in captured.err

    code = main(["inspect", "--home", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 2
    assert "auctelis inspect: --home requires --local." in captured.err
