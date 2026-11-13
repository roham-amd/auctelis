# Pilot tracker (5 × 30 days) — Authority Watch

Update a row when a pilot starts, renews, or drops the check.
Do not invent retention — leave `status` as `open` until evidence exists.

**Kill criterion (day 60):** fewer than five outside repos still running the
check → fall back to [`../PLAYBOOK.md`](../PLAYBOOK.md).

| Slot | Surface mix | Repo | Hook / Action | First lock (UTC) | Day-30 check | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Host MCP (doctor + hook) | _TBD_ | no | — | — | open | Authority Watch front door |
| 2 | Skills (Cursor/Claude) | _TBD_ | no | — | — | open | |
| 3 | Hooks + host settings | _TBD_ | no | — | — | open | |
| 4 | Lockless PR Action | _TBD_ | no | — | — | open | locked=false quickstart |
| 5 | Locked gate + CODEOWNERS | _TBD_ | no | — | — | open | approved-state upgrade |

**Status values:** `open` · `recruited` · `installed` · `retained_30d` · `dropped` · `declined`

## Metrics to capture per pilot

Log rows in [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv):

| Metric | How |
| --- | --- |
| `install_to_first_lock_minutes` | Wall clock from install to first `lock --home` or repo lock |
| `hook_still_installed_week4` | yes/no |
| `pr_output_useful` | Reviewer: yes / partial / no ("I wouldn't have noticed") |
| `false_positives` | Count of gated FPs in first two weeks |
| `action_still_enabled` | yes/no at day 30 |
| `unverified_share` | Share of growth PRs with protection unverified (target 0) |

## Recruitment checklist

- [ ] Confirm unrelated org/repo (not this product dogfood)
- [ ] Host path: `doctor` → `lock --home` → `hook install` under 5 minutes
- [ ] Team path: lockless Action first; upgrade to `locked=true` + CODEOWNERS
- [ ] Pin Action to git tag `v0.3.4` or commit SHA; `strict-ruleset: true`
- [ ] File labeled findings into `eval/holdout-labels.csv` / `eval/configs/`
- [ ] Re-check day 30 and update this tracker
