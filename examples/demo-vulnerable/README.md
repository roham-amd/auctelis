# Demo vulnerable repo (auctelis Authority Diff walkthrough)

Seeded fixtures that **should** produce gated findings. Not for production use.

```bash
# Preferred first screen: host authority delta
auctelis watch

# The canned repo fixture (for the PR-comment shape):
auctelis demo

# Hidden annotation layer, when you explicitly want findings:
auctelis scan examples/demo-vulnerable -o auctelis-out-demo --fail-on high
auctelis explain F-001 -o auctelis-out-demo
auctelis harden --findings auctelis-out-demo/findings.json
```

The same fixture is packaged at `auctelis/data/demo-vulnerable` so `auctelis demo`
does not require this repository tree.

Expected rule hits include: RULE-011 (unpinned), RULE-012 (literal secret),
RULE-013 (HTTP MCP), RULE-015 (curl|sh), RULE-016 (`pull_request_target` + agent),
RULE-017 (permission bypass), and content-based RULE-010.

The valuable output is `pr-comment.md` (Authority Diff), not the long report.
Use `auctelis scan --full` only when you need inventory graph / capabilities dumps.
