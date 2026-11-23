"""AUCT-065: auctelis inspect CLI + Trust Dossier attack/benign benchmarks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from auctelis.cli import main
from auctelis.cli.parser import build_parser
from auctelis_devtools.cli import main_dev

_REPO = Path(__file__).resolve().parents[1]
_ATTACK = _REPO / "examples" / "attack-replay"
_BENIGN = _REPO / "tests" / "fixtures" / "benign_components"


def test_public_cli_has_only_inspect_and_diff() -> None:
    parser = build_parser(include_dev=False)
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert set(sub.choices) == {"inspect", "diff"}
    with pytest.raises(SystemExit) as excinfo:
        main(["init", "--lockless"])
    assert excinfo.value.code == 2
    with pytest.raises(SystemExit) as help_exc:
        main_dev(["check", "--help"])
    assert help_exc.value.code == 0


def test_inspect_catches_all_10_attack_replay(capsys) -> None:
    dirs = sorted(p for p in _ATTACK.iterdir() if p.is_dir())
    assert len(dirs) == 10
    for path in dirs:
        code = main(["inspect", str(path), "--json", "--offline"])
        captured = capsys.readouterr()
        assert code == 1, f"{path.name}: exit {code}, stderr={captured.err!r}"
        doc = json.loads(captured.out)
        assert doc["red_flags"], f"{path.name}: expected non-empty red_flags"


def test_inspect_benign_benchmark_under_5pct_fp(capsys) -> None:
    dirs = sorted(p for p in _BENIGN.iterdir() if p.is_dir())
    assert len(dirs) == 20
    flagged = 0
    for path in dirs:
        code = main(["inspect", str(path), "--json", "--offline"])
        captured = capsys.readouterr()
        doc = json.loads(captured.out)
        if code != 0 or doc.get("verdict") != "UNVERIFIED_CLEAN" or doc.get("red_flags"):
            flagged += 1
    assert flagged == 0, f"expected 0/20 flagged, got {flagged}/20"
