# AgentSecBench-LLM participation guide (dataset 0.3.0)

Thank you for considering an independent audit submission. authdiff scores **offline JSON only**. We never call your model provider and never execute your submission files.

## What you receive

The **submitter package** (`authdiff benchmark submitter-package`):

- One task card per case (fixture path + instructions)
- Submission JSON schema
- This guide
- **No** ground-truth answers for any case (including held-out)

## What we need from you

For each case you audit, produce `LLM-NNN.json` matching the schema. Required metadata:

| Field | Why |
| --- | --- |
| `case_id` | Ties the file to a dataset case |
| `model` | Model identifier used |
| `agent_id` | Your agent / system name |
| `execution.produced_at_utc` | When the audit ran |
| `execution.fixture_ref` | Fixture path you audited |
| `execution.dataset_version_claimed` | Must be `"0.3.0"` |
| `execution.agent_version` / `model_version` | Versions if known |
| `execution.tools_available` / `permissions` | What the agent could do |
| `execution.configuration_notes` | System instructions summary or config notes |
| `execution.run_id` | Optional stable run identifier |
| `findings` | Your findings list (may be empty) |

Prefer **one independently developed agent configuration** per submission set. Multiple near-identical runs of the same setup do not increase diversity.

## How to run

1. Build or obtain the submitter package (maintainers: `uv run authdiff benchmark submitter-package -o DIR`).
2. For each task card, audit the listed fixture repository under **your** control.
3. Emit JSON findings offline; do not ask authdiff for answers or scores during collection.
4. Send the directory of `LLM-*.json` files to the maintainers for intake.

## Independence rules

- Held-out ground truth stays private.
- You will **not** receive case-level scoring feedback while collection is open.
- Do not modify files after you submit; intake checksums preserve the original bytes.
- Public cases may be used for practice; held-out cases are the evaluation set.

## What authdiff will not do with your files

- Will not execute submitted JSON, embedded scripts, or referenced paths as code.
- Will not treat invitations or incomplete uploads as scored evidence.
- Will not count templates, pilots, or maintainer samples as external evidence.
