# Pilot tracker (5 × 30 days) — Authority Diff

Update a row when a pilot starts, renews, or drops the check.
Do not invent retention — leave `status` as `open` until evidence exists.

**Kill criterion (day 60):** fewer than five outside repos still running the
check weekly, or fewer than three growth PRs actually reviewed → fall back to
[`../PLAYBOOK.md`](../PLAYBOOK.md).

| Slot | Surface mix | Repo | Action | First lock (UTC) | Day-30 check | Growth PRs reviewed | Taught them something | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | MCP + skills | _TBD_ | lockless | — | — | — | — | open | `auctelis init --lockless` |
| 2 | Instructions / rules | _TBD_ | lockless | — | — | — | — | open | |
| 3 | Enforce Action | _TBD_ | enforce | — | — | — | — | open | `init --enforce` |
| 4 | Advisory → enforce | _TBD_ | advisory→enforce | — | — | — | — | open | upgrade path |
| 5 | CODEOWNERS growth | _TBD_ | lockless→init | — | — | — | — | open | NEEDS_REVIEW → approve |

**Status values:** `open` · `recruited` · `installed` · `retained_30d` · `dropped` · `declined`

Leave a cell empty if the pilot declines or no evidence exists. Do not invent
retention, and do not replace `_TBD_` with a dogfood repo.

Metrics CSV: [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv) ·
Recruitment: [`RECRUITMENT.md`](RECRUITMENT.md)

## Recruitment checklist (0.1.5 report-first)

- [ ] Confirm unrelated org/repo (not this product dogfood)
- [ ] First: `auctelis check --github <org> --report out/` and forward the HTML/MD
- [ ] Second: `auctelis rollout reach-report.json` (dry-run, then `--apply`) or `auctelis init --lockless`
- [ ] Path under 10 minutes: org report → dry-run/apply Watch PRs → Watching comment
- [ ] Optional later: `init --owner team` / `--enforce`
- [ ] Pin Action to git tag `v0.1.5` (or commit SHA)
- [ ] Log row in `eval/pilot-metrics.csv` (surface_mix + install_path)
- [ ] Re-check day 30 and update this tracker
