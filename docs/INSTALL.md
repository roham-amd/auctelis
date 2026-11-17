# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (for the pinned tag install)

## Canonical install

Working install today is the **0.11.0** git tag (signed release assets are on
the GitHub Release). Prefer PyPI / `uvx` only after the index returns the
package.

```bash
# Working install (PyPI Trusted Publishing is wired; publish after pilots ask):
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.11.0#subdirectory=tools"
auctelis --version

# After PyPI is live:
# uv tool install --python 3.12 auctelis

auctelis diff --base origin/main            # aha before writing files
# Lockless: copy tools/auctelis/templates/auctelis-diff.yml → .github/workflows/
auctelis init --owner security              # comment-only; @ optional; PowerShell-safe
auctelis init --owner security --enforce    # optional locked + strict ruleset
auctelis check                              # repo authority vs AUTHORITY.lock
auctelis status --check                     # OK for comment-only; nonzero if enforce unarmed
auctelis why <name>                         # exact config path for one record
```

Bare `auctelis` runs `check` (repo-only). Product path:
**diff --base → init --owner team → check → gate** (tree-truth; lock optional pin).

An empty baseline is normal: the first growth PR is a CODEOWNERS review of
changed authority paths, not a forever `FAIL_CLOSED`. Use `auctelis demo` for
the canned fixture; product lock is inventory-only (no findings gate).

### Signed wheel (release assets)

GitHub Releases ship the wheel + `.cosign.bundle`. After downloading:

```bash
cosign verify-blob \
  --bundle auctelis-0.11.0-py3-none-any.whl.cosign.bundle \
  auctelis-0.11.0-py3-none-any.whl
```

Trusted Publishing workflow (reserve/publish the `auctelis` name):
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
auctelis --version
auctelis check --help
auctelis demo -o /tmp/auctelis-demo
```

See [`PRODUCT.md`](PRODUCT.md) for the command contract and
[`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) for the PR gate.

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.11.0 |
| Package `auctelis` | 0.11.0 |
