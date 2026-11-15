# Pilot tracker (5 × 30 days) — Authority Diff gate

Update a row when a pilot starts, renews, or drops the check.
Do not invent retention — leave `status` as `open` until evidence exists.

**Kill criterion (day 60):** fewer than five outside repos still running the
check weekly, or fewer than three growth PRs actually reviewed → fall back to
[`../PLAYBOOK.md`](../PLAYBOOK.md).

| Slot | Surface mix | Repo | Action | First lock (UTC) | Day-30 check | Growth PRs reviewed | Taught them something | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | MCP + skills | _TBD_ | no | — | — | — | — | open | `check` + lock |
| 2 | Instructions / rules | _TBD_ | no | — | — | — | — | open | |
| 3 | Enforce Action | _TBD_ | no | — | — | — | — | open | locked=true |
| 4 | Advisory → enforce | _TBD_ | no | — | — | — | — | open | `--advisory` then upgrade |
| 5 | CODEOWNERS growth | _TBD_ | no | — | — | — | — | open | NEEDS_REVIEW → approve |

**Status values:** `open` · `recruited` · `installed` · `retained_30d` · `dropped` · `declined`

Leave a cell empty if the pilot declines or no evidence exists. Do not invent
retention, and do not replace `_TBD_` with a dogfood repo.

## Metrics to capture per pilot

Log rows in [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv):

| Metric | How |
| --- | --- |
| `install_to_first_pr_diff_minutes` | Wall clock from install to first PR Authority Diff |
| `check_enabled_weekly` | yes/no — Action still required on default branch |
| `taught_them_something` | Reviewer: yes / partial / no |
| `pr_replies` | Reviewer replies on the PR comment: yes / partial / no |
| `false_positives` | Count of gated FPs in first two weeks |
| `growth_prs_reviewed` / `total_growth_prs` | CODEOWNER-reviewed growth |

## Recruitment checklist

- [ ] Confirm unrelated org/repo (not this product dogfood)
- [ ] Path: `check` → `lock --update` → `ci init --apply --owner @team` under 10 minutes
- [ ] Enforce Action (`locked=true`) + CODEOWNERS on `AUTHORITY.lock`
- [ ] Pin Action to git tag `v0.9.0` or commit SHA; `strict-ruleset: true`
- [ ] File labeled findings into `eval/holdout-labels.csv` / `eval/configs/`
- [ ] Re-check day 30 and update this tracker
