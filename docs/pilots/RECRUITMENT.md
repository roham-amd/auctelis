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
# In the pilot repo:
mkdir -p .github/workflows
# Copy tools/auctelis/templates/auctelis-diff.yml → .github/workflows/auctelis.yml
# Or curl the raw file from the auctelis tag, then open a PR that adds an MCP.
```

**B — Comment-only init**

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.9.1#subdirectory=tools"
auctelis diff --base origin/main
auctelis init --owner security   # advisory workflow + CODEOWNERS + lock
```

**C — Enforce (slot 3)**

```bash
auctelis init --owner security --enforce
```

## Logging

1. Add the repo to [`TRACKER.md`](TRACKER.md) (replace `_TBD_`).
2. Append/update the matching row in [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv).
3. Re-check day 30 (`action_still_enabled_day30`).

## PyPI readiness (do not publish until pilots ask)

Trusted Publishing is already wired in
[`.github/workflows/publish-pypi.yml`](../../.github/workflows/publish-pypi.yml).
Trigger only via `workflow_dispatch` after the PyPI project `auctelis` is claimed
and five pilots are running. Until then, lead install docs with the git-tag line.
