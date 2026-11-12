# Pilot tracker (5 × 30 days)

Update a row when a pilot starts, renews, or drops the check.
Do not invent retention — leave `status` as `open` until evidence exists.

| Slot | Surface mix | Repo | Action enabled | First lock (UTC) | Day-30 check | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | MCP registration | _TBD_ | no | — | — | open | |
| 2 | Skills (Cursor/Claude) | _TBD_ | no | — | — | open | |
| 3 | Hooks + host settings | _TBD_ | no | — | — | open | |
| 4 | Plugin / connector perms | _TBD_ | no | — | — | open | |
| 5 | CI agent/MCP workflows | _TBD_ | no | — | — | open | |

**Status values:** `open` · `recruited` · `installed` · `retained_30d` · `dropped` · `declined`

## Metrics to capture per pilot

Log rows in [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv):

| Metric | How |
| --- | --- |
| `install_to_first_lock_minutes` | Wall clock from install to committed `AUTHORITY.lock` |
| `pr_output_useful` | Reviewer: yes / partial / no |
| `false_positives` | Count of gated FPs in first two weeks |
| `action_still_enabled` | yes/no at day 30 |
| `unverified_share` | Share of growth PRs with protection unverified |

## Recruitment checklist

- [ ] Confirm unrelated org/repo (not this product dogfood)
- [ ] Pin Action to git tag or commit SHA
- [ ] Run adoption ceremony PR (`BASELINE_ADOPTED`) with human CODEOWNERS review
- [ ] Confirm ruleset / branch protection for code-owner review
- [ ] File labeled findings into `eval/holdout-labels.csv`
- [ ] Re-check day 30 and update this tracker
