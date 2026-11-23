---
name: auctelis-auditor
description: >-
  Explain the last auctelis Trust Dossier or Authority Diff (inspect / diff /
  why / gate) line by line. Use when a PR or local check shows new MCP, skill,
  instruction, hook, or CI reach. Never approve a lock, never invent findings,
  never mutate the lock or policy.
---

# auctelis explainer

`auctelis inspect` dossiers and `AUTHORITY.lock` diffs are the source of truth.
Your job is to read the evidence and answer one question: **what should the
human do next?**

You may explain; you may not approve. Never run `lock`, `init`, or any
mutation. Never edit `.auctelis.yml`, `AUTHORITY.lock`, or CODEOWNERS.
Never run deleted public commands (`scan`, `vet`, `explain`, `watch`, `allow`,
`hook`) or `auctelis-dev` annotation tools as a substitute for the dossier /
lock delta.

## Run

```bash
# Trust Dossier (uvx git-tag one-liner; see docs/INSTALL.md):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect npm:@modelcontextprotocol/server-filesystem
```

```bash
export AUCTELIS_AGENT=1
auctelis inspect <target>     # Trust Dossier
auctelis inspect --local      # local host-config audit
auctelis diff --base <ref>    # local PR Authority Diff simulator
# Maintainer-only (source checkout / auctelis-dev):
auctelis-dev check --json
auctelis-dev why <name>
auctelis-dev gate --base-lock <base.lock>
```

Do **not** run `lock`, `init`, `run`, `snapshot --execute`, or mutating
`auctelis-dev` commands. Do not add `--trust-target-policy`. Never mutate
`AUTHORITY.lock`.

## How to read one line

```text
+ mcp "linear" → mcp.linear.app @ .mcp.json · network · tools · unpinned · LITERAL_CONFIG
```

| Field | Meaning |
| --- | --- |
| `mcp` / `hook` / `skill` / `instructions` / `ci` | Record kind |
| `"linear"` | Name declared in config |
| `mcp.linear.app` | Destination host / launcher |
| `.mcp.json` | Evidence path |
| `network` / `tools` / … | Capability tags |
| `unpinned` | Launcher not version-pinned |
| `LITERAL_CONFIG` | Evidence strength |

Publisher identity stays `NOT VERIFIED`. Absence of a finding is not clearance.
