# External validation (scoped)

Strategic Week 4 was intentionally limited to **one** unrelated real GitHub
repository (not a ten-repo pilot matrix).

## Run

```bash
authdiff open microsoft/playwright-mcp -o docs/pilots/results/external-one
```

## Result — `microsoft/playwright-mcp`

| Field | Value |
| --- | --- |
| Commit | `404be8eb89abecff77a55152b6d843d140c78372` |
| Product / tools (at scan time) | authdiff **3.9.1** / authdiff **0.12.1** |
| Follow-up | **3.10.0+** demotes ordinary RULE-007 CI noise; regenerate under **1.0.0** before citing |
| Verdict | `REJECT` / PR decision `BLOCK` |
| Components | 15 |
| Gated findings | 11 (1 HIGH, 9 MEDIUM, 1 LOW) |
| Capabilities | 4 |
| Coverage | 13% SUPPORTED (2/15); PARTIAL=13 |
| Primary blocker | AUTHDIFF-RULE-016 — `pull_request_target` + agent-related steps in `.github/workflows/revision.yml` |
| Dominant noise | AUTHDIFF-RULE-007 on CI workflows (unattended automation) |

Slim exemplars (full JSON dumps are gitignored — regenerate with the command above):

- [`results/external-one/pr-comment.md`](results/external-one/pr-comment.md)
- [`results/external-one/scan-summary.txt`](results/external-one/scan-summary.txt)
- [`results/external-one/profile.json`](results/external-one/profile.json)

## Honest takeaways

1. First-run `open`/`vet` against a public MCP-related repo works without executing target code.
2. The Authority Diff PR comment surfaces the high-impact grant first (`RULE-016`).
3. Coverage honesty is visible: PARTIAL/MANUAL_ONLY gaps are reported; absence of findings ≠ safe.
4. RULE-007 on ordinary publish/release workflows is noisy for “pre-install authority” — worth a Week 3 precision pass, not proof the gate is wrong.
5. This is **one** external scan, not independent detection-quality validation and not AgentSecBench evidence.

## Not in scope here

Multi-repo pilot matrices, recruiter outreach, and CI-adoption metrics remain on
[`../ROADMAP.md`](../ROADMAP.md) for later.
