"""CLI wiring for ``check --resolve-pins`` (AUCT-050)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from auctelis.cli import main
from auctelis.pin_resolve import resolve_pins_in_report


def test_resolve_pins_requires_pins_or_report(capsys):
    assert main(["check", "--resolve-pins"]) == 2
    assert "--resolve-pins" in capsys.readouterr().out


def test_resolve_pins_on_report_is_additive(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    cfg = root / ".cursor"
    cfg.mkdir(parents=True)
    (cfg / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "demo": {
                        "command": "npx",
                        "args": ["-y", "@demo/mcp"],
                        "env": {"TOKEN": "x"},
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"

    def fake_resolve(report, *, fetcher=None, now=None):
        return resolve_pins_in_report(
            report,
            fetcher=lambda url: (200, {"dist-tags": {"latest": "3.2.1"}}),
            now=datetime(2026, 11, 22, tzinfo=UTC),
        )

    import auctelis.pin_resolve as pin_resolve

    monkeypatch.setattr(pin_resolve, "resolve_pins_in_report", fake_resolve)

    code = main(["check", str(root), "--report", str(out), "--resolve-pins", "--json"])
    assert code in {0, 1}
    doc = json.loads((out / "reach-report.json").read_text(encoding="utf-8"))
    items = doc.get("pins", {}).get("items") or []
    assert items
    assert items[0].get("resolved_pin") == "@demo/mcp@3.2.1"
    assert items[0].get("resolved_at") == "2026-11-22"
    assert "<exact-version>" in (items[0].get("config_snippet") or "")
