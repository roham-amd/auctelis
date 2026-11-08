# Demo vulnerable repo (authdiff Authority Diff walkthrough)

Seeded fixtures that **should** produce gated findings. Not for production use.

```bash
# Preferred first-run path (works from wheel + git install):
authdiff demo

# Or scan this checkout directory directly:
authdiff scan examples/demo-vulnerable -o authdiff-out-demo --fail-on high
authdiff explain F-001 -o authdiff-out-demo
authdiff harden --findings authdiff-out-demo/findings.json
```

The same fixture is packaged at `authdiff/data/demo-vulnerable` so `authdiff demo`
does not require this repository tree.

Expected rule hits include: RULE-011 (unpinned), RULE-012 (literal secret),
RULE-013 (HTTP MCP), RULE-015 (curl|sh), RULE-016 (`pull_request_target` + agent),
RULE-017 (permission bypass), and content-based RULE-010.

The valuable output is `pr-comment.md` (Authority Diff), not the long report.
Use `authdiff scan --full` only when you need inventory graph / capabilities dumps.
