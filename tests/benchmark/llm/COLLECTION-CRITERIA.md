# Collection window and closure criteria (EVAL 0.3.0)

Defined **before** accepting results. Do not move the goalposts after seeing scores.

## Window

| Field | Value |
| --- | --- |
| Contract | `AgentSecBench-LLM-EVAL-0.3.0` |
| Dataset | **0.3.0** (frozen) |
| Collection status | `open` |
| Opened (UTC) | `2026-11-04` |
| Target close (UTC) | `2026-12-04` or when minimum evidence is met, whichever is later if still below minimum |
| Hard stop (UTC) | `2026-12-18` — close even if below minimum; publish honest partial report |

Maintainers may **extend** the target close once if diversity is insufficient, but must not change scoring criteria or GT. Any criteria change requires a **new** evaluation contract version.

## Minimum evidence for a “meaningful” external report

All of the following:

1. **≥ 3** valid external intakes (`provenance=external`, `ok=true`)
2. **≥ 3** distinct agent configurations (framework/model/config fingerprint differ in a documented way)
3. Each counted intake covers **≥ 2** held-out cases (LLM-004/005/006/008), or the report flags incomplete coverage per agent
4. Original submission checksums preserved in the vault
5. Frozen contract still verifies (`authdiff benchmark contract verify`)

If the hard stop arrives below this bar, publish a report that states the shortfall. Keep **N** visible. Do not pad with pilots or templates.

## During collection

- No case-level scoring feedback to participants
- No silent edits to 0.3.0 GT, rubric, or scorer floors
- Defects → `CANDIDATE-IMPROVEMENTS.md` for a future version

## After closure

1. Freeze the vault registry for the evaluation cut (`collection closed` note in status)
2. Score held-out with `--provenance external`
3. Publish transparent report (conditions, sample sizes, dimensions, limitations)
4. No leaderboard / “best agent” ranking
