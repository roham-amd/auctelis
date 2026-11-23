# Pilot recruitment (5 outside repos + Trust Dossier concierge)

Do **not** count `roham-amd/auctelis` dogfood. Leave `_TBD_` / empty CSV cells
until a real outside repo is installed. Days 3–30: collect outside Trust
Dossiers (`inspect` / IssueOps), log each row in [`TRACKER.md`](TRACKER.md),
then paste the lockless Action workflow on pilot repos.

## Pitch (copy/paste)

> Auctelis decides in 10 seconds whether you can trust an MCP server, skill,
> hook, or plugin — then posts one PR comment when agent reach grows. Browse
> [`dossiers/CATALOG.json`](../../dossiers/CATALOG.json) or paste a six-line
> workflow — no lockfile required on day one. Optional enforce later.

## Install paths

**A — Trust Dossier aha (preferred first contact)**

```bash
# Package dossier (no install ceremony):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect npm:@modelcontextprotocol/server-filesystem

# Read-only local host configs:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect --local

# Local Authority Diff vs a git base:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis diff --base origin/main
```

Zero-install: open an Issue with
[Request a dossier](../../.github/ISSUE_TEMPLATE/inspect_request.yml).

**B — Lockless Action (Watch PRs)**

Paste the lockless workflow from
[`docs/examples/sample-reach-report.md`](../examples/sample-reach-report.md)
(or click **Watch PRs** when linked). Product CLI stays `inspect` + `diff`;
legacy `check` / `init` / `gate` live on `auctelis-dev` from a source checkout.

**C — Enforce (slot 3, from a source checkout)**

```bash
cd tools && uv sync --all-packages --locked
uv run auctelis-dev init --owner security --enforce
```

## Logging

1. Add the repo to [`TRACKER.md`](TRACKER.md) (replace `_TBD_`).
2. Append/update the matching row in [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv).
3. Re-check day 30 (`action_still_enabled_day30`).

## PyPI readiness (claim → bump+flip → publish → live probe → tag)

Trusted Publishing is wired in
[`.github/workflows/publish-pypi.yml`](../../.github/workflows/publish-pypi.yml).

1. Claim `auctelis` on PyPI and add a Trusted Publisher
   (owner roham-amd / repo auctelis / workflow publish-pypi.yml / env pypi).
2. Bump+flip PR: set `pypi_live` to `true` in `canonical/release-manifest.json`
   **and** `AUCTELIS_PYPI_DEFAULT="true"` in both `action.yml` copies so first-run
   docs lead with bare `uvx auctelis` and tagged Actions try PyPI.
3. Publish that flipped commit with `publish-pypi.yml` (`workflow_dispatch`).
4. Live probe: poll `https://pypi.org/pypi/auctelis/<ver>/json` until HTTP 200,
   then run `auctelis-dev build pypi-check --live`.
5. Tag the release only after the live probe is HTTP 200.

Until that flip lands, install docs lead with the git-tag line and tagged
Actions use bundled `tools/` with zero PyPI-404 warnings. Pilots should start
from
`uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect <target>`
then paste the lockless Action. On GHES or any host that cannot reach
github.com, maintainers can pass `--action-sha <40-hex>` on `auctelis-dev init`
(offline; no tag lookup).
