# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (only for the checkout / git-tag install)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## One-line install (canonical)

PyPI `auctelis` is not live yet (`pypi_live=false`). Use the release tag
(release assets are cosign-signed; the git tag itself is not):

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect npm:@modelcontextprotocol/server-filesystem
```

For a persistent CLI:

```bash
uv tool install --python 3.12 "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools"
auctelis --version
```

Cutover order (after the PyPI name is claimed and Trusted Publishing is set):
claim → bump+flip PR (`pypi_live=true` + both `AUCTELIS_PYPI_DEFAULT="true"` +
docs lead with `uvx auctelis inspect`) → publish → live probe → tag. Until then,
tagged Action runs use bundled `tools/` and do not warn on PyPI 404.

## First run

```bash
# 1. Trust dossier for a package:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect npm:@modelcontextprotocol/server-filesystem

# 2. Read-only audit of local agent configs:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect --local

# 3. Authority Diff vs a git base:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis diff --base origin/main
```

Bare `auctelis` runs `inspect`. Product path:
**inspect → inspect --local → diff --base**.

Zero-install dossiers: [`dossiers/CATALOG.json`](../dossiers/CATALOG.json) ·
[Request a dossier](../.github/ISSUE_TEMPLATE/inspect_request.yml).

Commands are documented in the [`CLI-REFERENCE`](CLI-REFERENCE.md).

## Fallback installs

Use these when you already have a downloaded wheel, or after PyPI is live and
the index is temporarily unreachable.

```bash
# Downloaded wheel (signed release assets are on the GitHub Release):
uv tool install --python 3.12 ./auctelis-0.1.11-py3-none-any.whl
```

### Signed wheel (release assets)

GitHub Releases ship the wheel + `.cosign.bundle`. After downloading:

```bash
cosign verify-blob \
  --bundle auctelis-0.1.11-py3-none-any.whl.cosign.bundle \
  auctelis-0.1.11-py3-none-any.whl
```

Trusted Publishing workflow:
[`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).
Trigger via `workflow_dispatch` after the PyPI project is claimed. The workflow
asserts the index returns 200 for the published version.

## From a checkout

```bash
cd tools
uv sync --locked
uv run auctelis inspect npm:@modelcontextprotocol/server-filesystem --offline
uv run auctelis inspect --local
uv run auctelis diff --base origin/main
# Maintainer surface (workspace member tools/dev):
uv run auctelis-dev build all
```

## Verify

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis --version
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect --help
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis diff --help
```

See [`PRODUCT.md`](PRODUCT.md) for the command contract and
[`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) for the PR gate.

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.1.11 |
| Package `auctelis` | 0.1.11 |
