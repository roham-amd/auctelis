---
name: auctelis-auditor
description: >-
  Explain the last auctelis Authority Diff (check / diff lock / gate) line by
  line. Use when a PR or local check shows new MCP, skill, instruction, hook,
  or CI reach. Never approve a lock, never invent findings, never run the
  scanner as a substitute for the lock delta.
---

# auctelis explainer

`AUTHORITY.lock` and `auctelis check` are the source of truth. Your job is to
read the delta and answer one question: **what should the human do next?**

You may explain; you may not approve. Never run `lock`, `ci init`,
`watch --seal`, `allow`, `watch --arm`, or `hook install`. Never edit
`.auctelis.yml`, `AUTHORITY.lock`, CODEOWNERS, or hooks.

## Run

```bash
# Install once (git tag; PyPI is not live yet):
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.8.0#subdirectory=tools"
```

```bash
export AUCTELIS_AGENT=1
auctelis check                # repo authority vs AUTHORITY.lock
auctelis check --json         # authority-diff/1
auctelis diff lock <base> <head>
auctelis why <name>
```

Archived host path (optional): `auctelis watch --delta-only`, `hook status`.

Do **not** run `lock`, `watch --seal`, `allow`, `watch --arm`, `hook install`,
`ci init`, `run`, `snapshot --execute`, or `auctelis-dev` commands. Do not add
`--trust-target-policy`.

## How to read one line

```text
+ mcp "linear" → mcp.linear.app @ .mcp.json · network · tools · unpinned · publisher NOT VERIFIED
```

| Field | Meaning |
| --- | --- |
| `mcp` / `hook` / `skill` / `instructions` / `ci` | Record kind |
| `"linear"` | Name declared in config |
| `→ host` / `launcher` / `@ path` | Destination or config file |
| capability bits | network, secrets, execute, tools, … |
| `publisher NOT VERIFIED` | Identity is not attested |

## Verdict vocabulary

| Verdict | Meaning |
| --- | --- |
| `LOCKED` | Matches committed lock |
| `BASELINE_NEEDED` | No lock yet — human should `lock --update` |
| `NEEDS_REVIEW` | Growth — CODEOWNER must approve |
| `FAIL_CLOSED` | Unusable lock / coverage gap |

Absence of a finding is not a clearance. Prefer exact file paths from the cards.
