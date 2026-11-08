# AgentSecBench external intake channel

Goal: receive the **first valid independent** AgentSecBench-LLM submission.

| Metric | Current |
| --- | --- |
| Valid external intakes (N) | **0** |
| Dataset / contract | **0.3.0** (frozen) |
| Channel status | Open |

Pilots, maintainer samples, and templates **do not** increment N.

## How independent agents submit

1. Open a GitHub issue with the **AgentSecBench submission** template, **or**
   contact maintainers via the security/participation docs.
2. Obtain the submitter package (no ground truth):
   ```bash
   uv run authdiff benchmark submitter-package -o /tmp/asb-submitter
   ```
3. Audit fixtures offline with your agent; emit `LLM-*.json` per case.
4. Deliver a directory of submission JSON files to maintainers.
5. Maintainers run:
   ```bash
   uv run authdiff benchmark intake /path/to/submissions \
     --agent-id YOUR_AGENT --provenance external
   ```

## Maintainer checklist (first external intake)

1. `aesa benchmark contract verify` → ok
2. `aesa benchmark intake … --dry-run` → ok
3. Real intake (no `--dry-run`) → vault entry + REGISTRY line
4. `aesa benchmark intakes` shows `valid_external >= 1`
5. Update `EXTERNAL-EVALUATION-REPORT` honestly (do not invent a leaderboard)

## What AESA will not do

- Count invitations, issue comments, or incomplete uploads as N
- Execute submission files
- Reveal held-out ground truth during an open collection window
- Relabel pilot/sample provenance as `external`

Participation guide: [`../tests/benchmark/llm/PARTICIPATION.md`](../tests/benchmark/llm/PARTICIPATION.md)
