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
# In the pilot repo — report first, then paste the workflow:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.15.0#subdirectory=tools" auctelis check --report out/
# Forward out/reach-report.html to the team, then:
mkdir -p .github/workflows
# Copy tools/auctelis/templates/auctelis-diff.yml → .github/workflows/auctelis.yml
# Or curl the raw file from the auctelis tag v0.15.0, then open a PR that adds an MCP.
```

**B — Comment-only init**

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.15.0#subdirectory=tools" auctelis check
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.15.0#subdirectory=tools" auctelis diff --base origin/main
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.15.0#subdirectory=tools" auctelis init --owner security   # advisory workflow + CODEOWNERS + lock
```

**C — Enforce (slot 3)**

```bash
auctelis init --owner security --enforce
```

## Logging

1. Add the repo to [`TRACKER.md`](TRACKER.md) (replace `_TBD_`).
2. Append/update the matching row in [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv).
3. Re-check day 30 (`action_still_enabled_day30`).

## PyPI readiness (claim name, then publish)

Trusted Publishing is wired in
[`.github/workflows/publish-pypi.yml`](../../.github/workflows/publish-pypi.yml).
Claim the `auctelis` project on PyPI, trigger `workflow_dispatch`, then flip
`pypi_live` to `true` in `canonical/release-manifest.json` so first-run docs
lead with bare `uvx auctelis`. Until then, install docs lead with the git-tag
line. Pilots should start from `check --report` before the workflow.
