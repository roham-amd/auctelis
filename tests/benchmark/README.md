# AgentSecBench

Detection-quality benchmarks for agent-ecosystem security assessments.

**Release note:** suite versions are pinned in `canonical/versions.json`. LLM dataset/rubric versions and checksums live in `llm/DATASET.json`.

## Modes (keep separate)

| Command | What it measures | Invokes models? |
| --- | --- | --- |
| `authdiff benchmark run` | Deterministic inventory + Guard rule smoke cases | No |
| `authdiff benchmark rules` | Per-rule positive/negative/ambiguous fixtures | No |
| `authdiff benchmark governance` | LLM dataset checksums + version pin | No |
| `authdiff benchmark contract verify` | Frozen evaluation contract + pins | No |
| `authdiff benchmark submitter-package -o DIR` | Task cards **without** ground truth | No |
| `authdiff benchmark intake DIR --agent-id ID` | Validate + vault preserve submissions (untrusted) | No |
| `authdiff benchmark intakes` | List vault registry / external evidence count | No |
| `authdiff benchmark collection-status` | Outreach funnel (invite ≠ intake) | No |
| `authdiff benchmark llm --validate-only` | GT contracts + integrity | No |
| `authdiff benchmark llm --submissions DIR [--split …]` | Offline scoring | No |
| `authdiff benchmark llm --submissions DIR --report [--provenance external]` | Transparent evaluation report (not a leaderboard) | No |

Do **not** cite deterministic pass rates as AI auditor accuracy. Do **not** publish a definitive leaderboard from maintainer pilots or eight cases alone. Templates and samples are **not** external evidence.

## Dataset 0.3.0 governance

- **Public:** LLM-001, 002, 003, 007 (development)
- **Held-out:** LLM-004, 005, 006, 008 (evaluation; do not tune against)
- Checksums: `llm/DATASET.json` → `case_checksums`
- Review process: `llm/reviews/REVIEW-PROCESS.md`
- Rubric: `llm/RUBRIC.md`
- External submissions: `llm/submissions/external/` (vault under `external/vault/`)
- Evaluation contract: `llm/EVALUATION-CONTRACT-0.3.0.json`
- Protocol: `llm/EVALUATION-PROTOCOL.md`
- External report: `llm/EXTERNAL-EVALUATION-REPORT-0.3.0.md`

```bash
authdiff benchmark governance
authdiff benchmark contract verify
authdiff benchmark llm --validate-only --split all
authdiff benchmark submitter-package -o ../authdiff-out/submitter-package-0.3.0
authdiff benchmark intakes
authdiff benchmark llm --submissions ../tests/benchmark/llm/submissions/pilots --split public --report
```

## Layout

- `fixtures/` — miniature repos for deterministic cases
- `cases/BENCH-*.json` — deterministic expectations
- `llm/cases/LLM-*.json` — expert ground truth
- `llm/reviews/` — independent reviews + adjudication
- `llm/submissions/sample-*` — scorer fixtures (not external)
- `llm/submissions/pilots/` — maintainer pilots (not external)
- `llm/submissions/templates/` — schema examples (not external)
- `llm/submissions/external/vault/` — append-only external intake storage
