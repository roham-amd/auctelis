# Demo vulnerable repo (auctelis Authority Diff walkthrough)

Seeded fixtures that **should** produce gated findings. Not for production use.

```bash
# Packaged walkthrough (preferred):
auctelis demo

# Or inventory this tree against AUTHORITY.lock:
auctelis check examples/demo-vulnerable

# Seal an intentional demo tree despite HIGH/CRITICAL annotations:
auctelis lock --update examples/demo-vulnerable --accept-gated
```

The same fixture is packaged at `auctelis/data/demo-vulnerable` so `auctelis demo`
does not require this repository tree.

Expected rule hits (maintainer annotation / demo fixture) include: RULE-011
(unpinned), RULE-012 (literal secret), RULE-013 (HTTP MCP), RULE-015 (curl|sh),
RULE-016 (`pull_request_target` + agent), RULE-017 (permission bypass), and
content-based RULE-010.

The valuable output is the Authority Diff / `pr-comment.md` shape, not a long
scanner report. Product path: check → lock --update → ci init --apply → gate.
