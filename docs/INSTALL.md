# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for the pinned tag install)

## Canonical install

Working install today is the **0.9.0** git tag (signed release assets are on
the GitHub Release). Prefer PyPI / `uvx` only after the index returns the
package.

```bash
# Working install (PyPI publish follows pilots):
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.9.0#subdirectory=tools"
auctelis --version

# After PyPI is live:
# uvx auctelis --version
# uv tool install --python 3.12 auctelis

auctelis init --owner security              # @ optional; PowerShell-safe
auctelis check                              # repo authority vs AUTHORITY.lock
auctelis status --check                     # nonzero if gate is not armed
auctelis why <name>                         # exact config path for one record
```

Bare `auctelis` runs `check` (repo-only). Product path:
**init --owner team → check → lock --update → gate** (tree-truth).

An empty baseline is normal: the first growth PR is a CODEOWNERS review of
changed authority paths, not a forever `FAIL_CLOSED`. Use `auctelis demo` for
the canned fixture; product lock is inventory-only (no findings gate).

### Signed wheel (release assets)

GitHub Releases ship the wheel + `.cosign.bundle`. After downloading:

```bash
cosign verify-blob \
  --bundle auctelis-0.9.0-py3-none-any.whl.cosign.bundle \
  auctelis-0.9.0-py3-none-any.whl
```

Trusted Publishing workflow (reserve/publish the `auctelis` name):
[`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).

## From a checkout

```bash
cd tools
uv sync --locked
uv run auctelis check .
uv run auctelis demo -o /tmp/auctelis-demo
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
| Product (`VERSION`) | 0.9.0 |
| Package `auctelis` | 0.9.0 |
