# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for the pinned tag install)

## Canonical install (current supported path)

PyPI is not live yet (coming). Until the index returns the package, install from
the **0.8.1** git tag:

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.8.1#subdirectory=tools"

auctelis init --owner @security             # preferred: policy + workflow + CODEOWNERS + lock
auctelis check                              # repo authority vs AUTHORITY.lock
auctelis status                             # lock / workflow / CODEOWNERS / protection
auctelis why <name>                         # exact config path for one record
```

Bare `auctelis` runs `check` (repo-only). Product path:
**init --owner @team → check → lock --update → gate**.

An empty baseline is normal: the first growth PR is a CODEOWNERS review of
`AUTHORITY.lock`, not a forever `FAIL_CLOSED`. Use `auctelis demo` for the
canned fixture; product lock is inventory-only (no findings gate).

### Once the package is on PyPI

When the index returns the package, prefer `uv tool install auctelis`. Until
then the git tag above is the only supported install.

Trusted Publishing workflow:
[`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).

## From a checkout

```bash
cd tools
uv sync --locked
uv run auctelis check .
uv run auctelis demo -o /tmp/auctelis-demo
```

## Docker (optional / deferred)

Docker is **not** part of the Authority Diff install. Prefer the git-tag CLI.

```bash
docker compose build
TARGET=/path/to/repo docker compose run --rm auctelis check /work
```

## Verify

```bash
auctelis --version
auctelis check --help
auctelis demo -o /tmp/auctelis-demo
```

See [`PRODUCT.md`](PRODUCT.md) for the command contract and
[`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) for the PR gate.

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.8.1 |
| Package `auctelis` | 0.8.1 |
