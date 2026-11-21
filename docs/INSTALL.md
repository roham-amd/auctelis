# Install auctelis

## Requirements

- Python **3.12+** (uv can fetch a managed interpreter)
- Git (only for the checkout / git-tag install)

## One-line install (canonical)

PyPI `auctelis` is not live yet (`pypi_live=false`). Use the release tag
(release assets are cosign-signed; the git tag itself is not):

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis check                     # aha: ranked reach cards (no lock needed)
```

**Zero-laptop org audit:** copy
[`auctelis-org-audit.yml`](auctelis-org-audit.yml) into your org `.github`
repo, click **Run workflow**, and read the Job Summary (no local `uv`/`git`
required). For private orgs, set secret `AUCTELIS_AUDIT_TOKEN` (Contents +
Metadata read).

Shareable audit artifact (step 2 of the first ten minutes):

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis check --report out/
```

For a persistent CLI:

```bash
uv tool install --python 3.12 "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools"
auctelis --version
```

Cutover order (after the PyPI name is claimed and Trusted Publishing is set):
claim → bump+flip PR (`pypi_live=true` + both `AUCTELIS_PYPI_DEFAULT="true"` +
docs lead with `uvx auctelis check`) → publish → live probe → tag. Until then,
tagged Action runs use bundled `tools/` and do not warn on PyPI 404.

## First run

```bash
cd your-repo
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis check                          # tree-truth reach (lock optional)
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis check --report out/             # HTML+MD+JSON+SBOM
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis check repo-a repo-b --report out/  # one ranked fleet report across repos
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis check --github your-org --report out/  # zero-clone org audit (GITHUB_TOKEN / GH_TOKEN / gh auth)
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis rollout out/reach-report.json            # dry-run Watch PRs for unwatched tier-2 repos
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis rollout out/reach-report.json --apply  # open those PRs (needs workflow scope)
# Org-reusable caller instead of the inline workflow:
#   uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis rollout out/reach-report.json --org-reusable your-org
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis init --lockless                 # one file: comment-only PR Watch (no owner/lock)
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis init --owner security          # full comment-only setup; @ optional; PowerShell-safe
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis init --owner security --enforce  # optional locked + strict ruleset
# commit → open install PR → first-run "Watching …" comment → later PRs get the diff
```

Bare `auctelis` runs `check` (repo-only). Product path:
**check → check --report → init (or the lockless workflow) → Action / gate** (tree-truth; lock
optional pin).

An empty baseline is normal: the first growth PR is a CODEOWNERS review of
changed authority paths, not a forever `FAIL_CLOSED`. Product lock is
inventory-only (no findings gate).

Advanced commands (`diff --base`, `check --pins`, `trust`, `status`, `lock`,
`why`, `demo`) are documented in the [README](../README.md#advanced-not-part-of-the-first-ten-minutes)
and the [`CLI-REFERENCE`](CLI-REFERENCE.md).

## Fallback installs

Use these when you already have a downloaded wheel, or after PyPI is live and
the index is temporarily unreachable.

```bash
# Downloaded wheel (signed release assets are on the GitHub Release):
uv tool install --python 3.12 ./auctelis-0.1.5-py3-none-any.whl
```

### Signed wheel (release assets)

GitHub Releases ship the wheel + `.cosign.bundle`. After downloading:

```bash
cosign verify-blob \
  --bundle auctelis-0.1.5-py3-none-any.whl.cosign.bundle \
  auctelis-0.1.5-py3-none-any.whl
```

Trusted Publishing workflow:
[`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml).
Trigger via `workflow_dispatch` after the PyPI project is claimed. The workflow
asserts the index returns 200 for the published version.

## From a checkout

```bash
cd tools
uv sync --locked
uv run auctelis check .
uv run auctelis check --report /tmp/auctelis-report
uv run auctelis demo -o /tmp/auctelis-demo
# Maintainer surface (workspace member tools/dev):
uv run auctelis-dev build all
```

## Org reusable workflow

Install once in your org `.github` repo using
[`auctelis-org-reusable.yml`](auctelis-org-reusable.yml), then each application
repo calls it with two lines (see that file).

## Verify

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis --version
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis check --help
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.5#subdirectory=tools" auctelis demo -o /tmp/auctelis-demo
```

See [`PRODUCT.md`](PRODUCT.md) for the command contract and
[`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) for the PR gate.

## Version alignment

| Surface | Version |
| --- | --- |
| Product (`VERSION`) | 0.1.5 |
| Package `auctelis` | 0.1.5 |
