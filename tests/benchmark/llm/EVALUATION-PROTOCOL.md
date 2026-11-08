# AgentSecBench-LLM evaluation protocol (dataset 0.3.0)

**Contract:** `EVALUATION-CONTRACT-0.3.0.json`  
**Status:** Frozen for collection. Do not alter 0.3.0 ground truth or scoring criteria after seeing results.

## 1. Pinned evaluation contract

Before accepting submissions, verify:

```bash
cd tools
uv run authdiff benchmark governance
uv run authdiff benchmark contract verify
```

Pins must match: dataset **0.3.0**, rubric **1.0.0**, submission schema **1.0**, scorer package ≥ **1.0.0**.

If criteria must change, publish a **new** contract/dataset version. Never mutate 0.3.0 quietly.

## 2. What submitters receive

Submitters get the **submitter package** (`authdiff benchmark submitter-package`):

- Task cards (case id, fixture path, instructions)
- **No** ground-truth findings for held-out cases
- Schema + protocol excerpt
- Permitted capabilities (offline audit only; no authdiff live provider calls)

They do **not** receive held-out answers or case-level scorer feedback during collection.

## 3. Invalid / incomplete submissions

| Condition | Handling |
| --- | --- |
| Schema invalid | Reject; record reason; do not score |
| Wrong/missing `dataset_version_claimed` | Reject |
| Missing `execution` metadata | Reject |
| Unknown `case_id` | Reject that file |
| Incomplete held-out set | Score available cases; flag `incomplete: true` |
| File changed after intake | Detect via checksum; mark `tampered`; exclude from report |

## 4. Provenance

Only `provenance: external` counts as external evidence.

`pilot`, `sample`, and `template` submissions must remain labeled and **must not** be described as external.

## 5. Reporting

Publish a transparent evaluation report (`--report --provenance external`):

- Conditions and pins
- Valid submission counts / sample size
- Detection, evidence, severity, unsupported-claim dimensions
- Per-case notes without ranking agents as “best”
- Limitations (dataset size; offline ≠ live evaluation)

## 6. Feedback to future versions

Defects discovered during evaluation go to `CANDIDATE-IMPROVEMENTS.md` for a **future** dataset/rubric version — not into frozen 0.3.0.
