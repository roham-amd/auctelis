# Auctelis product contract

**Product:** **Auctelis** (`auctelis`) — the authority lockfile and PR security gate for AI agents  
**Also known as:** Agent Authority Change Control  
**Release:** 0.3.3 · **Package:** `auctelis` 0.3.3 · **Lock:** v1 · **Rules:** pack 1.6 (001–022)

This page freezes what the product is, what it is not, and which commands are
primary. Research/archive trees were removed in 0.3.0.
Execution plan: [`ROADMAP.md`](ROADMAP.md).

---

## North star

> Know what authority your AI agents have, what changes when integrations are
> introduced, and whether those changes have been approved.

The real product is an **authority-change management and approval system** for
AI-agent integrations — not an audit framework, not a prompt library, and not a
generic vulnerability scanner.

One question drives the workflow:

> What new permissions, execution capabilities, destinations and delegation
> relationships are being introduced into our AI-agent environment, and who
> authorized them?

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

Public path: **doctor → lock → scan/gate → ci init** (demo / vet optional)

| Command | Job |
| --- | --- |
| `auctelis doctor` | Local host authority map (front door) |
| `auctelis demo` | Optional packaged fixture (always exits 0; prints `+/-` lock lines) |
| `auctelis vet` | Pre-install scan of a URL or path |
| `auctelis scan` / `check` | Repo Authority Diff (`--locked`, `--base-lock`) |
| `auctelis lock` | Write `AUTHORITY.lock` (`--accept-gated`, `--approval`) |
| `auctelis gate` | Label growth vs `--base-lock`; require CODEOWNERS + ruleset |
| `auctelis ci init --owner @team` | Policy + workflow + CODEOWNERS + initial lock |

Maintainer surfaces (`auctelis-dev` build / lint / corpus / deps) are secondary
and must not block the product loop.

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
