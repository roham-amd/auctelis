# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for a remote `vet`, if you use the hidden scanner)

## Canonical install (current supported path)

PyPI is not live yet, so the first command is always the pinned git tag:

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.7.0#subdirectory=tools"

auctelis check                         # repo authority vs AUTHORITY.lock
auctelis lock --update                 # seal AUTHORITY.lock in the repo
auctelis ci init --owner @security     # enforce workflow + CODEOWNERS
auctelis why <name>                    # exact config path for one record
```

Bare `auctelis` runs `check` (repo-only). Use `auctelis scan <path>` only when
you explicitly want the hidden annotation layer. `auctelis demo` is packaged
inside the wheel.

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
uv run auctelis check .
uv run auctelis demo -o /tmp/auctelis-demo
```

## Docker (optional / deferred)

Docker remains available for the hidden scan path but is **not** part of the
Authority Diff install. Prefer the git-tag CLI above.

```bash
docker compose build
TARGET=/path/to/repo docker compose run --rm auctelis scan /work -o /tmp/auctelis-out
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
| Product (`VERSION`) | 0.7.0 |
| Package `auctelis` | 0.7.0 |
