#!/usr/bin/env python3
"""Shallow-sample repos from eval/repos-25.txt and emit scan stubs for labeling.

Usage (from repo root, with auctelis on PATH):
  python eval/sample_repos.py [--limit 5] [--out eval/out]

Does not claim benchmark status — see docs/EVALUATION-PROTOCOL.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parent / "repos-25.txt",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", type=Path, default=Path("eval/out"))
    args = parser.parse_args()
    repos: list[str] = []
    for raw in args.manifest.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        repos.append(line)
        if len(repos) >= args.limit:
            break
    if not repos:
        print("No repos in manifest.", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    for spec in repos:
        name, _, ref = spec.partition("@")
        ref = ref or "HEAD"
        dest = args.out / name.replace("/", "__")
        print(f"==> {spec}")
        if not dest.exists():
            url = f"https://github.com/{name}.git"
            cmd = ["git", "clone", "--depth", "1"]
            if ref != "HEAD":
                cmd += ["--branch", ref]
            cmd += [url, str(dest)]
            subprocess.run(cmd, check=False)
        if not dest.is_dir():
            print(f"skip (clone failed): {spec}", file=sys.stderr)
            continue
        out = args.out / f"{name.replace('/', '__')}-auctelis-out"
        proc = subprocess.run(
            ["auctelis", "scan", str(dest), "-o", str(out), "--fail-on", "never"],
            check=False,
        )
        print(f"scan exit={proc.returncode} → {out}")
    print("Next: label findings into eval/holdout-labels.csv (blind review).")
    print("Pilot retention: update docs/pilots/TRACKER.md and eval/pilot-metrics.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
