# External evaluation protocol

How to judge authdiff quality without mistaking one demo scan for proof.

Related: [`ROADMAP.md`](ROADMAP.md), [`tests/rules/`](../tests/rules/),
[`tests/atlas/`](../tests/atlas/) (fixture corpus).

---

## Goals

1. Measure setup time to first meaningful Authority Diff.
2. Record false positives, missed detections, and unsupported surfaces.
3. Separate precision (gated findings that are correct) from recall (material authority missed).
4. Publish limitations honestly.

## Minimum pilot matrix (30-day target: 5 repos)

Select unrelated repositories that differ in agent configuration:

| Slot | Preferred surface mix |
| --- | --- |
| 1 | Public MCP server / client registration |
| 2 | Skill-heavy Cursor or Claude project |
| 3 | Hooks + host settings |
| 4 | Plugin / connector permissions |
| 5 | CI workflows with agent/MCP steps |

Historical note: one pre-0.3.0 external scan of `microsoft/playwright-mcp` (N=1)
existed under `docs/pilots/` and was removed in the shrink; regenerate before citing.

## Procedure (per repository)

```bash
authdiff open <owner/repo> -o authdiff-out-pilot/<slug>
# or, for a local checkout:
authdiff scan <path> -o authdiff-out-pilot/<slug> --full
```

Capture:

| Field | Source |
| --- | --- |
| Commit SHA | `audited_commit` / `profile.json` |
| Product / tooling / rule pack | `provenance` in `findings.json` |
| Component count + maturity mix | `coverage` |
| Gated findings | `SECURITY_FINDING` + `EXPOSURE` with evidence ids |
| Unsupported / unparsed | `coverage.manual_review_families`, `unparsed_agent_config_count` |
| Setup time | wall clock to first PR comment artifact |
| Reviewer disposition | accepted / rejected / deferred / remediated |

## Labeling rules

For each gated finding on a holdout set:

- **TP** — material authority or risk correctly described with evidence
- **FP** — finding should not gate (wrong class, weak evidence, ordinary inventory)
- **FN** — material authority expansion missed by adapters/rules
- **Ambiguous** — insufficient evidence for a confident determination (do not force a label)

`NAME_MARKER` findings must not count as independent HIGH/CRITICAL gate TPs.

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
