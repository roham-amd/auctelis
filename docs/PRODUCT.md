# Auctelis product contract

**Product:** **Auctelis** (`auctelis`) — evidence-backed trust dossiers for MCP servers, skills, hooks, and plugins  
**Release:** 0.1.11 · **Package:** `auctelis` 0.1.11 · **Lock:** v1 · **Rules:** pack 1.6 (core wheel + `auctelis-dev scan`)

This page freezes what the product is, what it is not, and which commands are
primary. Execution plan: [`ROADMAP.md`](ROADMAP.md).

---

## North star

> Decide in 10 seconds whether you can trust an MCP server, skill, hook, or plugin.

The product front door is a **Trust Dossier** (`auctelis inspect`) plus a
**local Authority Diff** (`auctelis diff --base`). Legacy lockfile / gate /
fleet commands live on `auctelis-dev` only. Host hooks, the allow store, and
tripwire heartbeats are **removed**.

One question drives the workflow:

> What can this package or local agent config reach, and what evidence supports
> that claim?

---

## Naming

| Name | Role |
| --- | --- |
| **Auctelis** | Product name and primary CLI |
| `auctelis` | Package name (`uvx --from git+…` today; `uvx auctelis` when pypi_live=true) |
| Trust Dossier | 4-part evidence report (`auctelis.trust_dossier.v1`) |
| `dossiers/CATALOG.json` | Zero-install published dossier index |
| `auctelis-out/` | Default artifact directory |
| Root `action.yml` (`uses: roham-amd/auctelis@vX`) | GitHub Action (`uses:` pin); runs `auctelis diff` |

---

## Primary commands

Public path: **inspect \<target\> | inspect --local | diff --base \<ref\>**

| Command | Job |
| --- | --- |
| `auctelis inspect <target>` | 4-part Trust Dossier for a package, URL, or local path |
| `auctelis inspect --local` | Read-only audit of installed local host configs (no hooks, no writes) |
| `auctelis diff --base <ref>` | Local Authority Diff; tree-truth first (`baseline_state=tree`), Action-parity |

Host stack (`watch` / `allow` / `hook` / `doctor`) and public `vet` / `harden` /
`explain` / `check` / `lock` / `gate` / `init` / `rollout` CLIs are **removed**
from the product wheel (maintainer surface: `auctelis-dev`). Research
scan/annotate stays out of the product wheel (`auctelis_research` /
`auctelis-dev` from source). Reach: [`REACH.md`](REACH.md).

**Exit codes (inspect):** `0` dossier printed · `1` usage / target error · `2` hard failure  
**Exit codes (diff --base):** `0` PASS · `1` NEEDS_REVIEW · `2` FAIL_CLOSED / invalid ref  
**Labels:** `GROWTH` | `REDUCTION` | `NONE`  
**Verdicts (diff):** `LOCKED` | `BASELINE_NEEDED` | `NEEDS_REVIEW` | `BASELINE_ADOPTED` | `FAIL_CLOSED` | `PASS`

---

## The four fields

Each authority record is user-facing as four facts:

1. **Name** — the MCP server, skill, hook, command, or instruction surface.
2. **Destination** — URL host or launcher (including hosts extracted from `curl|sh`).
3. **Capabilities** — network, secrets, execute, instructions, files, tools, approvals.
4. **Evidence strength** — `LITERAL_CONFIG` / `INFERRED_HINT` / `NAME_MARKER`.
   `NOT PARSED` is a coverage gap, not an evidence strength.

Publisher identity stays `NOT VERIFIED`. Absence of a finding is not a clearance.

---

## What it is / is not

**Is:** passive Trust Dossier + local Authority Diff for agent reach.  
**Is not:** a sandbox, runtime enforcer, certification badge, host consent broker,
or public 22-rule scanner product. Coverage language must stay honest
(`SUPPORTED` / `PARTIAL` / `MANUAL_ONLY` / `NOT VERIFIED`).

---

## Contracts

| Artifact | Doc |
| --- | --- |
| Reach model | [`REACH.md`](REACH.md) |
| Lock format | [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) |
| Gate / Action | [`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) |
| Install | [`INSTALL.md`](INSTALL.md) |
| Trust & safety | [`TRUST-AND-SAFETY.md`](TRUST-AND-SAFETY.md) |
