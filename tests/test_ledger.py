"""Unit tests for hook heartbeat + delta ledger."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.ledger import (
    append_delta,
    load_heartbeat,
    load_ledger,
    observed_state,
    record_heartbeat,
)


def test_ledger_caps_at_five(tmp_path: Path):
    home = tmp_path / "home"
    for i in range(7):
        append_delta([f"line-{i}"], home=home, host="session")
    ledger = load_ledger(home=home)
    assert len(ledger) == 5
    assert ledger[0]["lines"] == ["line-2"]
    assert ledger[-1]["lines"] == ["line-6"]


def test_quiet_heartbeat_preserves_prior_delta(tmp_path: Path):
    home = tmp_path / "home"
    record_heartbeat(
        home=home,
        had_delta=True,
        delta_lines=['+ mcp "x" → example.com'],
    )
    first = load_heartbeat(home=home)
    assert first is not None
    record_heartbeat(home=home, had_delta=False)
    second = load_heartbeat(home=home)
    assert second is not None
    assert second["had_delta"] is False
    assert second["last_delta"] == first["last_delta"]
    assert second["last_delta_lines"] == ['+ mcp "x" → example.com']


def test_corrupt_ledger_and_heartbeat_are_tolerated(tmp_path: Path):
    home = tmp_path / "home"
    root = home / ".auctelis"
    root.mkdir(parents=True)
    (root / "ledger.jsonl").write_text(
        "{not-json\n" + json.dumps({"fired_at": "t", "lines": ["ok"]}) + "\n",
        encoding="utf-8",
    )
    (root / "heartbeat.json").write_text("{broken", encoding="utf-8")
    assert load_heartbeat(home=home) is None
    assert load_ledger(home=home) == [{"fired_at": "t", "lines": ["ok"]}]


def test_observed_state_labels():
    assert observed_state(None) == "wired, not yet observed"
    assert observed_state({}) == "wired, not yet observed"
    assert observed_state({"last_fired": "2099-01-01T00:00:00Z"}).startswith("firing (last:")
