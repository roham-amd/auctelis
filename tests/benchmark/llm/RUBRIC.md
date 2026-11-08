# AgentSecBench-LLM scoring rubric

**Rubric version:** 1.0.0  
**Dataset version:** see `DATASET.json` (currently **0.3.0**, frozen with checksums)  
**Runner:** `authdiff benchmark llm` (never calls model APIs)

## What this measures

Offline comparison of agent-produced finding JSON against expert-reviewed ground truth.

| Dimension | Question | Primary metrics |
| --- | --- | --- |
| **Detection quality** | Did the auditor find the right issues (and avoid inventing others)? | precision, recall, F1 |
| **Evidence quality** | Are matched findings backed by evidence ids? | evidence_accuracy |
| **Severity quality** | Is severity within one step of ground truth? | severity_calibration |
| **Unsupported claims** | Did the auditor invent HIGH/CRITICAL/CONFIRMED claims without GT support? | hallucinated_claims |

These dimensions are scored **separately**. A high detection score does not imply good evidence quality.

## Matching rule

A predicted finding matches ground truth when normalized title token Jaccard overlap ≥ 0.35. Each GT finding matches at most one prediction.

## Floors

Each case may declare `score_floors` for CI regression of sample submissions. Floors are not published “accuracy claims.”

## What this is not

- Not live Cursor/Claude/Codex evaluation
- Not a substitute for human security review
- Not comparable to `authdiff benchmark run` or `authdiff benchmark rules` pass rates

## Reproducibility

1. Pin `dataset_version` + `rubric_version` from `DATASET.json` / `canonical/versions.json`.
2. Score with the same `authdiff` package version.
3. Keep submission JSON immutable (case_id, model label, findings).
4. Publish aggregate scores with dataset and rubric versions — never without them.
