# Auctelis product contract

**Product:** **Auctelis** (`auctelis`) — direnv allow for agent authority  
**Also known as:** Project Trust · Authority Watch · Agent Authority Change Control  
**Release:** 0.6.0 · **Package:** `auctelis` 0.6.0 · **Lock:** v1 · **Rules:** pack 1.6 (001–022)

This page freezes what the product is, what it is not, and which commands are
primary. Execution plan: [`ROADMAP.md`](ROADMAP.md).

---

## North star

> Nothing in a repo or your home gains reach until you've seen the diff and said OK.

The product is **Project Trust**: host + project inventory, a human-approved
lock / allow store, and a one-screen delta. Session hooks are **tripwires**
(observed via per-host heartbeat + optional `--probe`), not a sandbox. The
PR Authority Diff / gate is an optional team upsell. The 22-rule engine is an
annotation layer, not a public scanner product. There is no certification,
badge, sandbox, or runtime broker.

One question drives the workflow:

> What new permissions, execution capabilities, and destinations are being
> introduced (destination hosts — publisher identity stays NOT VERIFIED unless
> separately attested), and has a human approved that change?

---

## Naming

| Name | Role |
| --- | --- |
| **Auctelis** | Product name and primary CLI |
| `auctelis` | PyPI / import package name (git tag until published) |
| `.auctelis.yml` | Policy file |
| `auctelis-out/` | Default artifact directory |
| `.github/actions/auctelis-gate` | GitHub Action |
| `skills/auctelis-auditor` | Thin agent skill that **explains** CLI evidence |
| `plugins/claude`, `plugins/cursor` | Optional host bundles |

---

## Primary commands

Public path: **watch → watch --seal --accept \<digest\> → allow --accept \<digest\> → watch --arm → why \<name\> → hook status [--probe]**

| Command | Job |
| --- | --- |
| `auctelis watch` | One-screen declared authority (front door). First run = every sealable record + Accept digest |
| `auctelis watch --seal --accept <digest>` | Seal `~/.auctelis/AUTHORITY.lock` (human only; digest must match screen) |
| `auctelis allow --accept <digest>` | Allow current project authority hash (Project Trust) |
| `auctelis watch --arm` / `hook install` | Session + tripwire hooks (absolute interpreter paths) |
| `auctelis why <name>` | Exact config path / fields for one authority record |
| `auctelis hook status [--probe]` | Wired / firing per host; `--probe` proves tripwires deny |
| `auctelis demo` | Optional packaged fixture |

`scan` / `gate` / `ci` / `check` / `vet` remain callable for compatibility but
are hidden from default help. Rule IDs annotate a diff line; they do not become
the page. Reach definition: [`REACH.md`](REACH.md).

**Exit codes (watch):** `0` quiet / first-run summary · `1` sealed delta · `2` lock / seal-accept error  
**Exit codes (hook status --probe):** `0` probe pass · `1` probe fail  
**Labels:** `GROWTH` | `REDUCTION` | `NONE` — what the lock delta is.

Maintainer surfaces (`auctelis-dev` build / lint / corpus / deps) are secondary
and must not block the product loop. `run` / `snapshot` / `artifact-vet` stay on
`auctelis-dev` only.

---

## The four fields

Each authority record is user-facing as four facts:

1. **Name** — the MCP server, skill, hook, command, or host settings surface.
2. **Destination** — URL host or launcher (including hosts extracted from `curl|sh`).
3. **Capabilities** — network, secrets, execute, instructions, files, tools, approvals.
4. **Evidence strength** — `LITERAL_CONFIG` / `INFERRED_HINT` / `NAME_MARKER`.
   `NOT PARSED` is a coverage gap, not an evidence strength.

Permission posture (`prompt` / `auto` / `bypassPermissions`) and allow-lists are
first-class on Host Settings cards. Publisher identity and effective permission
stay `NOT VERIFIED`. Absence of a finding is not a clearance.

---

## What it is / is not

**Is:** passive, host-neutral inventory + sealed lock + project allow + delta + optional PR gate.  
**Is not:** a sandbox, runtime enforcer, certification badge, or second scanner
product. Coverage language must stay honest (`SUPPORTED` / `PARTIAL` /
`MANUAL_ONLY` / `NOT VERIFIED`).

---

## Contracts

| Artifact | Doc |
| --- | --- |
| `AUTHORITY.lock` | [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) |
| Guard scan | [`GUARD-SCAN.md`](GUARD-SCAN.md) |
| Policy | [`POLICY.md`](POLICY.md) |
| Rules | [`SECURITY-RULES.md`](SECURITY-RULES.md) |
| Reach | [`REACH.md`](REACH.md) |
