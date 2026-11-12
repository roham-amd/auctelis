# Install authdiff

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for `authdiff vet` of remote URLs)
- Optional: Docker for the digest-pinned image

## Canonical install (one command)

### Preferred (once PyPI is live)

```bash
uvx --from authdiff authdiff demo
uv tool install --python 3.12 authdiff
authdiff demo && authdiff doctor && authdiff lock
```

Trusted Publishing workflow: [`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).
Until the package appears on the index, use the git-tag fallback below.

`authdiff demo` is packaged inside the wheel (`authdiff/data/demo-vulnerable`) —
it works from every supported install path, including a bare wheel without the
repository `examples/` tree.

### Git-tag fallback (current supported path)

**One-shot demo** (`uvx` is ephemeral — it does not leave a persistent `authdiff` on PATH):

```bash
uvx --from "git+https://github.com/roham-amd/authdiff.git@v0.3.2#subdirectory=tools" authdiff demo
```

**Persistent tool install:**

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/authdiff.git@v0.3.2#subdirectory=tools"

authdiff demo
authdiff doctor
authdiff vet github.com/org/some-skill
authdiff scan .
authdiff lock
authdiff ci init --owner @you
authdiff gate --base-lock AUTHORITY.lock   # after a base lock exists
```

Bare `authdiff` (no subcommand) defaults to `authdiff scan .`.

Package and CLI name: **`authdiff`**. Maintainer commands: **`authdiff-dev`**.

Public mental model: **doctor → lock → scan/gate → ci init** (demo / vet optional).

## From a checkout

```bash
cd tools
uv sync --locked
uv run authdiff scan ../examples/demo-vulnerable
```

## Docker

```bash
docker compose build
TARGET=/path/to/repo docker compose run --rm authdiff scan /work -o /tmp/authdiff-out
```

Image base: `python:3.12.16-slim-trixie` (digest-pinned in `Dockerfile`).

## GitHub Action

See [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md) and `authdiff ci init` (writes a
**lock-first** workflow with `locked: true`).
Consumer recipe: [`authdiff-consumer-gate.example.yml`](authdiff-consumer-gate.example.yml).

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.3.1 |
| Package `authdiff` | 0.3.1 |
| `AUTHORITY.lock` schema | 1 |
| Rule pack | 1.6 |
