"""Mini-Atlas crawl harness — seed list + offline ledger writer.

Does not mass-crawl GitHub by default (rate limits / ToS). Provide a seed file
of public repos, or use ``--demo-seed`` for the bundled ~N starter set. Target
for credibility is **N ≥ 300** labeled findings over time; this module records
scan digests into ``docs/atlas/ledger/``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from authdiff.paths import repo_root
from authdiff.security.gating import is_gate_finding
from authdiff.security.scan import run_scan

DEMO_SEEDS: list[dict[str, str]] = [
    {"id": "demo-vulnerable", "path": "examples/demo-vulnerable", "class": "attack"},
    {"id": "benign-loglevel", "path": "tests/atlas/benign/node-mcp-loglevel", "class": "benign"},
    {
        "id": "benign-pinned-fs",
        "path": "tests/atlas/benign/pinned-filesystem",
        "class": "benign",
    },
    {
        "id": "attack-sessionstart",
        "path": "tests/atlas/attacks/sessionstart-env-exfil",
        "class": "attack",
    },
    {
        "id": "attack-mcp-auto",
        "path": "tests/atlas/attacks/mcp-auto-approve",
        "class": "attack",
    },
    {
        "id": "attack-base-url",
        "path": "tests/atlas/attacks/base-url-override",
        "class": "attack",
    },
]


def ledger_dir() -> Path:
    return repo_root() / "docs" / "atlas" / "ledger"


def load_seed_file(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: Any = data["repos"] if isinstance(data, dict) and "repos" in data else data
    if not isinstance(rows, list):
        raise ValueError("seed file must be a list or {repos: [...]}")
    return [r for r in rows if isinstance(r, dict)]


def scan_seed_row(row: dict[str, str], *, out_root: Path) -> dict[str, Any]:
    rel = row.get("path") or ""
    target = (repo_root() / rel).resolve() if rel else None
    if target is None or not target.exists():
        return {"id": row.get("id"), "ok": False, "error": f"missing path {rel}"}
    out = out_root / str(row.get("id") or target.name)
    scan, _payload, code = run_scan(target, output_dir=out, fail_on=None)
    gated = [f for f in scan.findings if is_gate_finding(f)]
    return {
        "id": row.get("id"),
        "class": row.get("class"),
        "path": rel,
        "ok": True,
        "exit_code": code,
        "finding_count": len(scan.findings),
        "gated_count": len(gated),
        "rules_fired": sorted({f.rule_id for f in gated}),
        "decision_hint": "BLOCK"
        if any(f.severity in {"CRITICAL", "HIGH"} for f in gated)
        else ("REVIEW" if gated else "NO-GATED-FINDINGS"),
    }


def run_crawl(
    *,
    seed_file: Path | None = None,
    demo_seed: bool = False,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    rows = DEMO_SEEDS if demo_seed or seed_file is None else load_seed_file(seed_file)
    if seed_file is not None and demo_seed:
        rows = load_seed_file(seed_file) + DEMO_SEEDS
    out_root = out_dir or (ledger_dir() / "runs" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    out_root.mkdir(parents=True, exist_ok=True)
    results = [scan_seed_row(row, out_root=out_root) for row in rows]
    summary = {
        "atlas_crawl_version": "0.1.0",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed_count": len(rows),
        "scanned_ok": sum(1 for r in results if r.get("ok")),
        "target_n_labeled_findings": 300,
        "current_gated_findings": sum(int(r.get("gated_count") or 0) for r in results),
        "results": results,
        "notes": [
            "Demo/seed crawl only — expand via seed JSON of public repos.",
            "Label findings blind before publishing precision; aggregate by default.",
        ],
    }
    (out_root / "crawl-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    # Rolling index
    index_path = ledger_dir() / "index.json"
    ledger_dir().mkdir(parents=True, exist_ok=True)
    index: dict[str, Any] = {"runs": [], "target_n": 300}
    if index_path.is_file():
        try:
            loaded = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                index = loaded
        except json.JSONDecodeError:
            pass
    runs = list(index.get("runs") or [])
    try:
        run_rel = str(out_root.resolve().relative_to(repo_root())).replace("\\", "/")
    except ValueError:
        run_rel = str(out_root.resolve())
    runs.append(
        {
            "path": run_rel,
            "seed_count": summary["seed_count"],
            "gated": summary["current_gated_findings"],
            "at": summary["generated_at_utc"],
        }
    )
    index["runs"] = runs[-50:]
    index["target_n"] = 300
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return summary
