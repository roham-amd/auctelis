# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for `auctelis vet` of remote URLs)
- Optional: Docker for the digest-pinned image

## Canonical install (one command)

### Preferred (once PyPI is live)

```bash
uvx --from auctelis auctelis doctor
uv tool install --python 3.12 auctelis
auctelis doctor && auctelis lock
```

Trusted Publishing workflow: [`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).
Until the package appears on the index, use the git-tag fallback below.

`auctelis demo` is packaged inside the wheel (`auctelis/data/demo-vulnerable`) —
it works from every supported install path, including a bare wheel without the
repository `examples/` tree.

### Git-tag fallback (current supported path)

**One-shot doctor** (`uvx` is ephemeral — it does not leave a persistent `auctelis` on PATH):

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.3.4#subdirectory=tools" auctelis doctor
```

**Persistent tool install:**

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.3.4#subdirectory=tools"

auctelis doctor
auctelis lock --home
auctelis hook install                      # session delta + PreToolUse lock
auctelis doctor --since-lock
auctelis vet github.com/org/some-skill
auctelis ci init --owner @you              # team upsell (lockless Action first)
auctelis demo                              # optional canned fixture
```

Bare `auctelis` (no subcommand) → `doctor` when the cwd has no `AUTHORITY.lock` /
`.auctelis.yml`; otherwise → `scan .`. A path or scan flags without a subcommand
still run `scan`.

Package and CLI name: **`auctelis`**. Maintainer commands: **`auctelis-dev`**.

Public mental model: **doctor → lock --home → hook install → (team) gate / ci init**.

## From a checkout

```bash
cd tools
uv sync --locked
uv run auctelis scan ../examples/demo-vulnerable
```

## Docker

```bash
docker compose build
TARGET=/path/to/repo docker compose run --rm auctelis scan /work -o /tmp/auctelis-out
```

Image base: `python:3.12.16-slim-trixie` (digest-pinned in `Dockerfile`).

## GitHub Action

See [`AUCTELIS-GATE.md`](AUCTELIS-GATE.md). Quickstart is **lockless-first**
(`locked: false`, `strict-ruleset: true`). `auctelis ci init --owner @team`
writes that lockless workflow plus CODEOWNERS; after sealing `AUTHORITY.lock`,
set `locked: true` on the Action step for the approved-state upgrade.
Consumer recipe: [`auctelis-consumer-gate.example.yml`](auctelis-consumer-gate.example.yml).

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.3.4 |
| Package `auctelis` | 0.3.4 |
| `AUTHORITY.lock` schema | 1 |
| Rule pack | 1.6 |
