# Auctelis product contract

**Product:** **Auctelis** (`auctelis`) — package-lock for agent authority  
**Also known as:** Authority Watch · Agent Authority Change Control  
**Release:** 0.3.4 · **Package:** `auctelis` 0.3.4 · **Lock:** v1 · **Rules:** pack 1.6 (001–022)

This page freezes what the product is, what it is not, and which commands are
primary. Research/archive trees were removed in 0.3.0.
Execution plan: [`ROADMAP.md`](ROADMAP.md).

---

## North star

> See what your agents can do, and what changed since you last said OK.

The real product is **Authority Watch**: host inventory + lock + session delta,
with the PR Authority Diff as the team upsell — not an audit framework, not a
prompt library, and not a generic vulnerability scanner.

One question drives the workflow:

> What new permissions, execution capabilities, and destinations are being
> introduced (destination hosts — publisher identity stays NOT VERIFIED unless
> separately attested), and has a human approved that change?

---

## Naming

| Name | Role |
| --- | --- |
| **Auctelis** | Product name and primary CLI |
| `auctelis` | PyPI / import package name |
| `.auctelis.yml` | Policy file |
| `auctelis-out/` | Default artifact directory |
| `.github/actions/auctelis-gate` | GitHub Action |
| `skills/auctelis-auditor` | Thin agent skill that **explains** CLI evidence |

---

## Primary commands

Public path: **doctor → lock --home → hook install → (team) gate / ci init**

| Command | Job |
| --- | --- |
| `auctelis doctor` | Local host authority map (front door) |
| `auctelis lock --home` / `lock` | Seal host or repo `AUTHORITY.lock` |
| `auctelis hook install` | Session-start delta + PreToolUse lock enforce |
| `auctelis vet` | Pre-install scan of a URL or path |
| `auctelis gate` | Label growth vs `--base-lock` (`--strict-ruleset` default on) |
| `auctelis ci init --owner @team` | Policy + lockless workflow + CODEOWNERS; set `locked: true` after seal |
| `auctelis demo` | Optional packaged fixture |
| `auctelis scan` / `check` | Repo annotations / lock drift (`--locked`) |

**One verdict vocabulary:** `PASS` | `GROWTH` | `NEEDS_REVIEW` | `BASELINE_ADOPTED`.
Scan severities annotate; they are not a second public `BLOCK` gate.

Maintainer surfaces (`auctelis-dev` build / lint / corpus / deps) are secondary
and must not block the product loop. `run` / `snapshot` / `artifact-vet` stay on
`auctelis-dev` only (kill-list demotion).

---

## What it is / is not

**Is:** passive, host-neutral inventory + rule engine + sealed lock + PR gate.  
**Is not:** a sandbox, runtime enforcer, or certification badge. Coverage language
must stay honest (`SUPPORTED` / `PARTIAL` / `MANUAL_ONLY` / `NOT VERIFIED`).

---

## Contracts

| Artifact | Doc |
| --- | --- |
| `AUTHORITY.lock` | [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) |
| Guard scan | [`GUARD-SCAN.md`](GUARD-SCAN.md) |
| Policy | [`POLICY.md`](POLICY.md) |
| Rules | [`SECURITY-RULES.md`](SECURITY-RULES.md) |
| Evidence | [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md) |
| PR gate | [`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) |
