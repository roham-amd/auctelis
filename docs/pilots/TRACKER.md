# Pilot tracker (5 × 30 days) — Authority Watch

Update a row when a pilot starts, renews, or drops the check.
Do not invent retention — leave `status` as `open` until evidence exists.

**Kill criterion (day 60):** fewer than five outside repos still running the
check → fall back to [`../PLAYBOOK.md`](../PLAYBOOK.md).

| Slot | Surface mix | Repo | Hook / Action | First lock (UTC) | Day-30 check | Hook status wk4 | Taught them something | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Host MCP (watch + hook) | _TBD_ | no | — | — | — | — | open | Authority Watch front door |
| 2 | Skills (Cursor/Claude) | _TBD_ | no | — | — | — | — | open | |
| 3 | Hooks + host settings | _TBD_ | no | — | — | — | — | open | |
| 4 | Lockless PR Action | _TBD_ | no | — | — | — | — | open | locked=false quickstart |
| 5 | Locked gate + CODEOWNERS | _TBD_ | no | — | — | — | — | open | approved-state upgrade |

**Status values:** `open` · `recruited` · `installed` · `retained_30d` · `dropped` · `declined`

Leave a cell empty if the pilot declines or no evidence exists. Do not invent
retention, and do not replace `_TBD_` with a dogfood repo.

## Metrics to capture per pilot

Log rows in [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv):

| Metric | How |
| --- | --- |
| `install_to_first_delta_minutes` | Wall clock from install to the first `watch` delta line |
| `hook_status_week4` | `auctelis hook status` answer at week 4 |
| `taught_them_something` | Reviewer: yes / partial / no ("I wouldn't have noticed") |
| `pr_replies` | Reviewer replies on the PR comment: yes / partial / no |
| `false_positives` | Count of gated FPs in first two weeks |
| `action_still_enabled_day30` | yes/no at day 30 |
| `unverified_growth_prs` / `total_growth_prs` | Growth PRs with protection unverified (target 0) |

## Recruitment checklist

- [ ] Confirm unrelated org/repo (not this product dogfood)
- [ ] Host path: `watch` → `watch --seal` → `watch --arm` under 5 minutes
- [ ] Team path: lockless Action first; upgrade to `locked=true` + CODEOWNERS
- [ ] Pin Action to git tag `v0.4.0` or commit SHA; `strict-ruleset: true`
- [ ] File labeled findings into `eval/holdout-labels.csv` / `eval/configs/`
- [ ] Re-check day 30 and update this tracker
