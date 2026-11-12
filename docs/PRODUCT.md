# authdiff product contract

**Product:** `authdiff` — the authority lockfile and PR security gate for AI agents  
**Also known as:** Agent Authority Change Control  
**Release:** 0.3.2 · **Package:** `authdiff` 0.3.2 · **Lock:** v1 · **Rules:** pack 1.6 (001–022)

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
| **authdiff** | Product name and primary CLI |
| `authdiff` | PyPI / import package name |
| `.authdiff.yml` | Policy file |
| `authdiff-out/` | Default artifact directory |
| `.github/actions/authdiff-gate` | GitHub Action |
| `skills/authdiff-auditor` | Thin agent skill that **explains** CLI evidence |

---

## Primary commands

Public path: **doctor → lock → scan/gate → ci init** (demo / vet optional)

| Command | Job |
| --- | --- |
| `authdiff demo` | Packaged aha (always exits 0; prints `+/-` lock lines) |
| `authdiff doctor` | Local host authority map |
| `authdiff vet` | Pre-install scan of a URL or path |
| `authdiff scan` / `check` | Repo Authority Diff (`--locked`, `--base-lock`) |
| `authdiff lock` | Write `AUTHORITY.lock` (`--accept-gated`, `--approval`) |
| `authdiff gate` | Label growth vs `--base-lock`; require CODEOWNERS + ruleset |
| `authdiff ci init --owner @team` | Policy + workflow + CODEOWNERS + initial lock |

Maintainer surfaces (`authdiff-dev` build / lint / corpus / deps) are secondary
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
| PR gate | [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md) |
