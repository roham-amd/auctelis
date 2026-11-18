# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (only for the checkout / fallback install)

## One-line install (canonical)

`uvx` runs the package without a permanent install (once PyPI `auctelis` is
published, `uvx auctelis check` also works directly):

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools" auctelis check                     # aha: ranked reach cards (no lock needed)
```

For a persistent CLI:

```bash
uv tool install --python 3.12 "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools"
auctelis --version
```

## First run

```bash
cd your-repo
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools" auctelis check                          # repo authority vs AUTHORITY.lock
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools" auctelis init --owner security          # comment-only; @ optional; PowerShell-safe
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools" auctelis init --owner security --enforce  # optional locked + strict ruleset
# commit → open install PR → first-run "Watching …" comment → later PRs get the diff
```

Bare `auctelis` runs `check` (repo-only). Product path:
**check → init (or the lockless workflow) → Action / gate** (tree-truth; lock
optional pin).

An empty baseline is normal: the first growth PR is a CODEOWNERS review of
changed authority paths, not a forever `FAIL_CLOSED`. Product lock is
inventory-only (no findings gate).

Advanced commands (`diff --base`, `check --pins`, `trust`, `status`, `lock`,
`why`, `demo`) are documented in the [README](../README.md#advanced-not-part-of-the-first-ten-minutes)
and the [`CLI-REFERENCE`](CLI-REFERENCE.md).

## Fallback installs

Use these only when the PyPI index cannot be reached.

```bash
# Git tag (signed release assets are on the GitHub Release):
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools"

# Or a downloaded wheel:
uv tool install --python 3.12 ./auctelis-0.12.2-py3-none-any.whl
```

### Signed wheel (release assets)

GitHub Releases ship the wheel + `.cosign.bundle`. After downloading:

```bash
cosign verify-blob \
  --bundle auctelis-0.12.2-py3-none-any.whl.cosign.bundle \
  auctelis-0.12.2-py3-none-any.whl
```

Trusted Publishing workflow:
[`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).
Trigger via `workflow_dispatch` after the PyPI project is claimed — do not invent
publish success until the index returns 200.

## From a checkout

```bash
cd tools
uv sync --locked
uv run auctelis check .
uv run auctelis demo -o /tmp/auctelis-demo
```

## Verify

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools" auctelis --version
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools" auctelis check --help
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.12.2#subdirectory=tools" auctelis demo -o /tmp/auctelis-demo
```

See [`PRODUCT.md`](PRODUCT.md) for the command contract and
[`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) for the PR gate.

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.12.2 |
| Package `auctelis` | 0.12.2 |
