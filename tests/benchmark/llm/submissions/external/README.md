# External submissions (offline evaluation 0.3.0)

authdiff scores **submitted JSON only**. It does not call model providers.
Every intake is **untrusted data**: schema/size checks and checksums only — never executed.

Templates live under `../templates/` — they are **not** external evidence.

Participant guide: `../../PARTICIPATION.md`  
Maintainer outreach: `../../OUTREACH.md`  
Closure criteria: `../../COLLECTION-CRITERIA.md`

## Before you submit

1. Obtain the submitter package (task cards **without** ground truth):

```bash
cd tools
uv run authdiff benchmark submitter-package -o ../authdiff-out/submitter-package-0.3.0
```

2. Run your agent against the listed fixtures under your own control.
3. Emit one `LLM-00N.json` per case (schema `schemas/agentsecbench-submission.schema.json`).
4. Set `execution.dataset_version_claimed` to `"0.3.0"`.
5. Include agent/model versions, tools/permissions notes, and fixture references.

## Intake (maintainers)

```bash
uv run authdiff benchmark intake DIR --agent-id <id> --provenance external --dry-run
uv run authdiff benchmark intake DIR --agent-id <id> --provenance external
uv run authdiff benchmark collection-status
```

Valid intakes are checksummed into `vault/received/<run_id>/`. Invalid payloads are rejected and not written as evidence.

## Scoring (after collection closes)

```bash
uv run authdiff benchmark llm --submissions vault/received/<run_id> --split held_out --report --provenance external
```

During collection, submitters do **not** receive case-level scoring feedback on held-out cases.

## Provenance labels

| Label | Counts as external evidence? |
| --- | --- |
| `external` | Yes, if intake `ok` and vault-written |
| `pilot` / `sample` / `template` | No |
