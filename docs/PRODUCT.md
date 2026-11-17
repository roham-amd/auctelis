# Auctelis product contract

**Product:** **Auctelis** (`auctelis`) — the authority lockfile and PR gate for what AI agents can reach  
**Release:** 0.11.0 · **Package:** `auctelis` 0.11.0 · **Lock:** v1 · **Rules:** pack 1.6 (research / `auctelis_research` only)

This page freezes what the product is, what it is not, and which commands are
primary. Execution plan: [`ROADMAP.md`](ROADMAP.md).

---

## North star

> Nothing in a repo gains reach until a human has seen the Authority Diff and said OK.

The product is a **GitHub-native Authority Diff + enforcement gate**: one
extractor, one lock schema, one diff engine, one PR comment, one Action.
Locally, `auctelis check` is the repo preflight. Host hooks, the allow store,
and tripwire heartbeats are **removed** — not the weekly habit.

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

Public path: **diff --base → lockless workflow or init --owner team → check → gate**

| Command | Job |
| --- | --- |
| `auctelis diff --base <ref>` | Local PR Authority Diff simulator (aha; no files written) |
| `auctelis init --owner team` | Comment-only setup (default); `--enforce` for locked gate (`@` optional) |
| `auctelis check` | Repo authority vs `AUTHORITY.lock` (front door; inventory-only) |
| `auctelis status` | Lock / workflow / CODEOWNERS / protection summary (`--check` OK for comment-only) |
| `auctelis lock --update` | Write / refresh the committed lock (optional pin) |
| `auctelis ci init` | Legacy alias of init |
| `auctelis gate --base-lock base.lock` | PR Authority Diff + CODEOWNERS / ruleset gate |
| `auctelis why <name>` | Exact config path / fields for one record |
| `auctelis demo` | Optional packaged fixture |

Host stack (`watch` / `allow` / `hook` / `doctor`) and public `vet` / `harden` /
`explain` CLIs are **removed**. The product gate is **tree-truth**: head
authority is always derived from the working tree; a committed `AUTHORITY.lock`
is an optional pin (drift-checked when present). Default Action is
**comment-only**; research scan/annotate stays out of the product wheel
(`auctelis_research` / `auctelis-dev` from source). Reach tiers: inferred doc
links stay comment-only; execute/secrets/new MCP fail under enforce. Reach:
[`REACH.md`](REACH.md).

**Exit codes (check):** `0` quiet / first-run · `1` sealed delta · `2` lock error  
**Labels:** `GROWTH` | `REDUCTION` | `NONE`  
**Verdicts:** `LOCKED` | `BASELINE_NEEDED` | `NEEDS_REVIEW` | `BASELINE_ADOPTED` | `FAIL_CLOSED` | `PASS`  
(`FAIL_CLOSED` = unusable / missing base lock for gate — not the empty-baseline state. First growth after an empty seal is CODEOWNERS review.)

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
