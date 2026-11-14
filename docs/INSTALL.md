# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for a remote `vet`, if you use the hidden scanner)
- Optional: Docker for the digest-pinned image

## Canonical install (current supported path)

PyPI is not live yet, so the first command is always the pinned git tag:

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.5.0#subdirectory=tools"

auctelis                    # highlights + inventory (first run) or sealed delta
auctelis watch --seal       # human baseline in ~/.auctelis/AUTHORITY.lock
auctelis watch --arm        # session + tripwire hooks for Cursor and Claude Code
auctelis hook status        # wired / not yet observed / firing (heartbeat)
auctelis why <name>         # exact config path for one authority record
```

Bare `auctelis` runs `watch`; it is never a scanner. Use `auctelis <path>` or
`auctelis scan <path>` only when you explicitly want the hidden annotation
layer. `auctelis demo` is packaged inside the wheel and works from every install
path.

### Once the package is on PyPI

PyPI is not live yet. When the index returns the package, this section will
document the `uv tool install auctelis` path; until then the git tag above is
the only supported install.

Trusted Publishing workflow:
[`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).

## From a checkout

```bash
cd tools
uv sync --locked
uv run auctelis watch --home /tmp/auctelis-home
uv run auctelis demo -o /tmp/auctelis-demo
```

## Docker

```bash
docker compose build
TARGET=/path/to/repo docker compose run --rm auctelis scan /work -o /tmp/auctelis-out
```

Image base: `python:3.12.16-slim-trixie` (digest-pinned in `Dockerfile`).

## GitHub Action (optional team upsell)

Not required for the individual consent-ledger path. See
[`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) if a team wants PR Authority Diff.
Quickstart is **lockless-first** (`locked: false`). `auctelis ci init` remains
callable but is hidden from default help.
Consumer recipe: [`auctelis-consumer-gate.example.yml`](auctelis-consumer-gate.example.yml).

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.5.0 |
| Package `auctelis` | 0.5.0 |
| `AUTHORITY.lock` schema | 1 |
| Rule pack | 1.6 |
