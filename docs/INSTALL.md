# Install authdiff

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for `authdiff open` / `vet` of remote URLs)
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
uvx --from "git+https://github.com/YOUR_GITHUB_ORG/authdiff.git@v1.0.0#subdirectory=tools" authdiff demo
```

**Persistent tool install:**

```bash
uv tool install --python 3.12 \
  "git+https://github.com/YOUR_GITHUB_ORG/authdiff.git@v1.0.0#subdirectory=tools"

authdiff demo
authdiff doctor
authdiff open github.com/org/some-skill
authdiff scan .
authdiff lock
authdiff ci init
```

Bare `authdiff` (no subcommand) defaults to `authdiff scan .`.

Package and CLI name: **`authdiff`**. Maintainer commands: **`authdiff-dev`**.

Public mental model: **demo → doctor → vet → scan → lock → ci**.

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

See [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md) and `authdiff ci init` (writes an advisory workflow stub).
Consumer recipe: [`authdiff-consumer-gate.example.yml`](authdiff-consumer-gate.example.yml).

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 1.0.0 |
| Package `authdiff` | 1.0.0 |
| `AUTHORITY.lock` schema | 2 |
| Rule pack | 1.6 |
