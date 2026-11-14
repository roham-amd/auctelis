# External evaluation protocol

How to judge auctelis quality without mistaking one demo scan for proof.

Related: [`ROADMAP.md`](ROADMAP.md), [`tests/rules/`](../tests/rules/),
[`tests/atlas/`](../tests/atlas/) (fixture corpus).

---

## Goals

1. Measure setup time to first meaningful Authority Diff.
2. Record false positives, missed detections, and unsupported surfaces.
3. Separate precision (gated findings that are correct) from recall (material authority missed).
4. Publish limitations honestly.

## Minimum pilot matrix (30-day target: 5 repos)

Select unrelated repositories that differ in agent configuration.
Live tracker: [`pilots/TRACKER.md`](pilots/TRACKER.md). Metrics: [`../eval/pilot-metrics.csv`](../eval/pilot-metrics.csv).

| Slot | Preferred surface mix |
| --- | --- |
| 1 | Public MCP server / client registration |
| 2 | Skill-heavy Cursor or Claude project |
| 3 | Hooks + host settings |
| 4 | Plugin / connector permissions |
| 5 | CI workflows with agent/MCP steps |

Self-dogfood of `roham-amd/auctelis` does **not** count. Historical pre-0.3.0
pilot notes were removed in the shrink; cite only rows with day-30 retention evidence.

## Procedure (per repository)

```bash
auctelis watch                       # one-screen delta vs the host seal
auctelis watch --seal                # human baseline
auctelis watch --arm                 # Cursor + Claude hooks
# Hidden annotation layer, if you need finding-level detail:
auctelis scan <path> -o auctelis-out-pilot/<slug> --full
```

Capture:

| Field | Source |
| --- | --- |
| Commit SHA | `audited_commit` / `profile.json` |
| Product / tooling / rule pack | `provenance` in `findings.json` |
| Component count + maturity mix | `coverage` |
| Delta cards | `auctelis watch` / `watch --delta-only` |
| Unsupported / unparsed | `coverage.manual_review_families`, `unparsed_agent_config_count` |
| Setup time | wall clock to the first delta line |
| Reviewer disposition | accepted / rejected / deferred / remediated |
| Did the line teach them something? | yes / partial / no (tracker) |

## Labeling rules

For each gated finding on a holdout set:

- **TP** — material authority or risk correctly described with evidence
- **FP** — finding should not gate (wrong class, weak evidence, ordinary inventory)
- **FN** — material authority expansion missed by adapters/rules
- **Ambiguous** — insufficient evidence for a confident determination (do not force a label)

`NAME_MARKER` findings must not count as independent HIGH/CRITICAL gate TPs.

## Current fixture score (no detection claim yet)

Only configs with a fixture are scored. Run:

```bash
python eval/score_configs.py
```

The 0.5.0 tree has five fixtures: four expected-growth configs and one benign
README. The current differ scores **TP=4, FP=0, FN=0, TN=1** on those five.
That is a regression check, not a precision claim — publish a TP/FP number only
after outside, independently labeled configs exist.

## Reporting

Publish a short note (issue or `docs/` page) with:

1. Repo + commit
2. Coverage honesty (supported ratio)
3. Top gated findings with evidence ids
4. False-positive / miss notes
5. Explicit statement: *N scans ≠ independent product validation*

Do **not** cite AgentSecBench as external validation while external submissions remain N=0.

## Success thresholds (targets)

| Metric | 30-day | 90-day |
| --- | --- | --- |
| First meaningful scan | &lt; 2 min | &lt; 2 min |
| Gated findings with evidence refs | 100% | 100% |
| Unsupported surfaces reported | 100% | 100% |
| HIGH/CRITICAL precision on labeled holdout | establish baseline | ≥ 90% |
| External repos evaluated | 5 | 15+ |
| Passive scans executing target code | 0 | 0 |
