# Independent ground-truth review process

**Goal:** Make AgentSecBench trustworthy by separating authoring from acceptance.

## Roles

| Role | Responsibility |
| --- | --- |
| Author | Drafts fixture + proposed ground truth |
| Reviewer A / B | Independently mark findings before seeing each other |
| Adjudicator | Resolves disagreements; records rationale |

Reviewers must **not** see another reviewer’s conclusions before submitting their own.

## Case types required in every frozen dataset

- Positive (expected findings)
- Negative (empty GT; inventions are hallucinations)
- Ambiguous (weak signals / capability-only)

## Workflow

1. Author opens a draft under `cases/` with `review.status: draft`.
2. Two reviewers complete `reviews/independent/R*-<case_id>.json` independently.
3. Adjudicator writes `reviews/adjudication/ADJ-<case_id>.json`.
4. On acceptance, case `review.status` becomes `accepted` and dataset checksums are refreshed (`authdiff benchmark governance`).
5. Public vs held-out assignment is recorded in `DATASET.json` **before** external evaluation.

## Disagreement handling

Disagreements are expected. Record:

- Conflicting finding titles / severities / statuses
- Whether the case remains positive, negative, or ambiguous
- Final adjudicated ground truth
- Explicit “do not claim” bans

## What acceptance means

Accepted means reviewers agree the GT is suitable for offline scoring — **not** that real-world exploitation was proven.
