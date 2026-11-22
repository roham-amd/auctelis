# Pilot recruitment (5 outside repos)

Do **not** count `roham-amd/auctelis` dogfood. Leave `_TBD_` / empty CSV cells
until a real outside repo is installed.

## Pitch (copy/paste)

> Auctelis posts one PR comment that shows what new reach an AI-agent config
> change gives (MCP, skills, hooks, instructions). Paste a six-line workflow —
> no lockfile required on day one. Optional enforce later.

## Install paths

**A — Lockless (preferred first contact)**

```bash
# In the pilot repo — report first, then the one-file workflow:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis check --report out/
# Forward out/reach-report.html to the team, then:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis init --lockless
# The workflow-only install PR gets one PASS "Watching" comment. A PR that also
# adds an MCP/hook stays NEEDS_REVIEW with its delta cards.
# Auditing several pilot repos at once:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis check repo-a repo-b --report out/
# Zero-clone org audit (no local clones; needs GITHUB_TOKEN / gh auth):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis check --github your-org --report out/
# Or zero-laptop: paste docs/auctelis-org-audit.yml → Actions → Run workflow.
```

**B — Comment-only init**

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis check
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis diff --base origin/main
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis init --owner security   # advisory workflow + CODEOWNERS + lock
```

**C — Enforce (slot 3)**

```bash
auctelis init --owner security --enforce
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
[`docs/auctelis-org-audit.yml`](../auctelis-org-audit.yml) (zero laptop install)
or
`uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis check --github <org> --report out/`
(uses `gh auth`), forward the HTML report, then run
`uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.8#subdirectory=tools" auctelis rollout out/reach-report.json --show-body`
(dry-run; prints the evidence-backed PR body) and the same command with
`--apply --pin-sha` (immutable `roham-amd/auctelis@<sha> # vX`). On GHES or any
host that cannot reach github.com, pass `--action-sha <40-hex>` instead
(offline; no tag lookup and no fallback to `https://api.github.com`). The same
offline pin is `init --lockless --action-sha <40-hex>` (`--pin-sha` on
`init --lockless` does the tag lookup). `--org-reusable` skips the Action pin.
Optional `--repo owner/repo` targets one pilot. Track merges with
`rollout --status` (the token needs `Pull requests: read`).
