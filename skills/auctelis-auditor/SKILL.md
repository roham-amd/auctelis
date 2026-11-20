---
name: auctelis-auditor
description: >-
  Explain the last auctelis Authority Diff (check / diff / why / gate) line by
  line. Use when a PR or local check shows new MCP, skill, instruction, hook,
  or CI reach. Never approve a lock, never invent findings, never mutate the
  lock or policy.
---

# auctelis explainer

`AUTHORITY.lock` and `auctelis check` are the source of truth. Your job is to
read the delta and answer one question: **what should the human do next?**

You may explain; you may not approve. Never run `lock`, `init`, `ci init`, or any
mutation. Never edit `.auctelis.yml`, `AUTHORITY.lock`, or CODEOWNERS.
Never run deleted public commands (`scan`, `vet`, `explain`, `watch`, `allow`,
`hook`) or `auctelis-dev` annotation tools as a substitute for the lock delta.

## Run

```bash
# Run once (uvx git-tag one-liner; `uvx auctelis check` see docs/INSTALL.md; fallback in docs/INSTALL.md):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.17.0#subdirectory=tools" auctelis check
```

```bash
export AUCTELIS_AGENT=1
auctelis check                # repo authority vs AUTHORITY.lock
auctelis check --json         # authority-diff/1
auctelis diff --base <ref>    # local PR Authority Diff simulator
auctelis diff lock <base> <head>
auctelis why <name>
auctelis gate --base-lock <base.lock>   # read-only growth labels
```

Do **not** run `lock`, `init`, `ci init`, `run`, `snapshot --execute`, or
`auctelis-dev` commands. Do not add `--trust-target-policy`. Never mutate
`AUTHORITY.lock`.

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
| `BASELINE_ADOPTED` | First seal / empty baseline ceremony (not forever `FAIL_CLOSED`) |
| `NEEDS_REVIEW` | Growth — CODEOWNER must approve |
| `FAIL_CLOSED` | Unusable lock / missing base for gate (not the empty-baseline state) |

Absence of a finding is not a clearance. Prefer exact file paths from the cards.
