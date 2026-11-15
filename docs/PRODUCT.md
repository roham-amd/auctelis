# Auctelis product contract

**Product:** **Auctelis** (`auctelis`) — the authority lockfile and PR review for what AI agents can reach  
**Release:** 0.7.0 · **Package:** `auctelis` 0.7.0 · **Lock:** v1 · **Rules:** pack 1.6 (001–022)

This page freezes what the product is, what it is not, and which commands are
primary. Execution plan: [`ROADMAP.md`](ROADMAP.md).

---

## North star

> Nothing in a repo gains reach until a human has seen the Authority Diff and said OK.

The product is a **GitHub-native Authority Diff + enforcement gate**: one
extractor, one lock schema, one diff engine, one PR comment, one Action.
Locally, `auctelis check` is the repo preflight. Host hooks, the allow store,
and tripwire heartbeats are archived — not the weekly habit.

One question drives the workflow:

> What new permissions, execution capabilities, and destinations are being
> introduced, and has a human approved that change?

---

## Naming

| Name | Role |
| --- | --- |
| **Auctelis** | Product name and primary CLI |
| `auctelis` | Package name (git tag until PyPI publishes) |
| `.auctelis.yml` | Policy file |
| `AUTHORITY.lock` | Sealed repo authority |
| `auctelis-out/` | Default artifact directory |
| `.github/actions/auctelis-gate` | GitHub Action |

---

## Primary commands

Public path: **check → lock --update → ci init --owner @team → gate**

| Command | Job |
| --- | --- |
| `auctelis check` | Repo authority vs `AUTHORITY.lock` (front door; no host scan) |
| `auctelis lock --update` | Write the committed lock from the current tree |
| `auctelis ci init --owner @team` | Enforce workflow + CODEOWNERS + lock (`--advisory` optional) |
| `auctelis gate --base-lock …` | PR Authority Diff + CODEOWNERS / ruleset gate |
| `auctelis why <name>` | Exact config path / fields for one record |
| `auctelis demo` | Optional packaged fixture |

`watch` / `allow` / `hook` / `doctor` are archived (callable, hidden from help).
`scan` remains a hidden annotation layer. Reach: [`REACH.md`](REACH.md).

**Exit codes (check):** `0` quiet / first-run · `1` sealed delta · `2` lock error  
**Labels:** `GROWTH` | `REDUCTION` | `NONE`  
**Verdicts:** `LOCKED` | `BASELINE_NEEDED` | `NEEDS_REVIEW` | `BASELINE_ADOPTED` | `FAIL_CLOSED`

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

**Is:** passive, repo-scoped inventory + sealed lock + PR Authority Diff + optional CODEOWNERS gate.  
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
