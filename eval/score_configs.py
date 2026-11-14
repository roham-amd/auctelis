#!/usr/bin/env python3
"""Score the config fixtures that actually exist.

No detection claim is allowed until this prints a TP/FP/FN count. Only configs
with a fixture are scored; add a row when you add a fixture.

Usage (from the repo root):

    python eval/score_configs.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "tools"))

from auctelis.authority_lock import build_authority_lock, diff_authority_locks

_EMPTY = {"version": 1, "records": [], "policy_hash": None, "mcp_tools": {}}


def _labels() -> dict[str, dict[str, str]]:
    path = _ROOT / "eval" / "holdout-labels.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["config_id"]: row for row in csv.DictReader(handle)}


def _fixture_dirs() -> list[Path]:
    return [
        path
        for path in sorted((_ROOT / "eval" / "configs").iterdir())
        if path.is_dir() and any(item.is_file() for item in path.iterdir())
    ]


def score() -> list[dict[str, str]]:
    labels = _labels()
    results: list[dict[str, str]] = []
    for fixture in _fixture_dirs():
        label = labels.get(fixture.name, {})
        expected = str(label.get("expected_growth") or "").strip().lower()
        delta = diff_authority_locks(_EMPTY, build_authority_lock(fixture))
        summary = delta.get("summary") or {}
        actual = bool(summary.get("meaningful_authority_change"))
        if expected in {"yes", "true", "1"}:
            outcome = "TP" if actual else "FN"
        elif expected in {"no", "false", "0"}:
            outcome = "FP" if actual else "TN"
        else:
            outcome = "UNLABELED"
        records = list((delta.get("changes") or {}).get("added") or [])
        capabilities = sorted(
            {
                str(cap)
                for record in records
                for cap in (record.get("capabilities") or [])
                if cap
            }
        )
        results.append(
            {
                "config_id": fixture.name,
                "surface": str(label.get("surface") or ""),
                "expected_growth": expected,
                "actual_growth": "yes" if actual else "no",
                "capabilities": ", ".join(capabilities),
                "tp_fp_fn": outcome,
                "records": str(len(records)),
            }
        )
    return results


def main() -> int:
    results = score()
    out = _ROOT / "eval" / "labeled-results.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    counts = {
        key: sum(1 for row in results if row["tp_fp_fn"] == key)
        for key in ("TP", "FP", "FN", "TN")
    }
    for row in results:
        print(
            f"{row['config_id']}: expected={row['expected_growth']} "
            f"actual={row['actual_growth']} -> {row['tp_fp_fn']} "
            f"({row['records']} records; {row['capabilities'] or 'no capabilities'})"
        )
    print(
        f"\nTP={counts['TP']} FP={counts['FP']} FN={counts['FN']} TN={counts['TN']} "
        f"· wrote {out.relative_to(_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
