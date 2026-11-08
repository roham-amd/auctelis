# authdiff product contract

**Product:** `authdiff` — the authority lockfile and PR security gate for AI agents  
**Also known as:** Agent Authority Change Control  
**Release:** 1.0.0 · **Package:** `authdiff` 1.0.0 · **Lock:** v1 · **Rules:** pack 1.6 (001–022)

This page freezes what the product is, what it is not, and which commands are
primary. Historical methodology lives under [`archive/`](../archive/).
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

## Primary mental model (three questions)

1. **What authority do I already have?** → `authdiff doctor` / `authdiff` (defaults to `scan .`)
2. **What authority does this change introduce?** → `authdiff open` / lock diff / PR comment
3. **Is that change approved?** → `AUTHORITY.lock` + CODEOWNERS + CI gate

Everything else is secondary.

### First-user journey

1. `authdiff demo` — see Authority Diff on a vulnerable fixture
2. Persistent install (`uv tool install` from the git tag)
3. `authdiff doctor` → `open` → `scan .` → `lock` → `ci init`
4. Protect `AUTHORITY.lock` with CODEOWNERS; experience expansion on the next PR

---

## Core command tier

Public mental model (enforced in `tools/authdiff/cli/parser.py` as
`CORE_PUBLIC_COMMANDS`; review/advanced commands stay callable but are omitted
from brief `--help`):

```text
demo → doctor → vet/open → scan/check → lock → ci
```

| Tier | Commands |
| --- | --- |
| **Core (public)** | `demo`, `doctor`, `open`/`vet`, `authdiff`/`scan`/`check` (bare → scan), `lock`, `ci init`, `check --locked` |
| **Review (optional)** | `explain`, `diff lock`, `delta`, `annotate`, `fix`/`harden` — hidden from brief help |
| **Advanced / opt-in** | `run`, `snapshot`, `artifact-vet`, `atlas`, `lsp-validate`, manifests (hidden from brief `--help`) |
| **Maintainer** | `authdiff-dev` only (`build`, `lint`, `corpus`, `benchmark`, …) |

Four jobs with distinct trust boundaries:

| Job | Command | Trust boundary |
| --- | --- | --- |
| Host environment | `doctor` | Developer's local machine |
| Pre-install admission | `open` / `vet` | External component / clone (passive) |
| Repository scan | `scan` | Target repository contents |
| Approved state + gate | `lock` / `ci` | Human-owned; agents must not mutate |

---

## Authority layers (product contract)

| Layer | Meaning |
| --- | --- |
| **Declared** | What the integration says it requires |
| **Configured** | What host/repo configuration appears to expose |
| **Effective** | What the execution environment actually permits |
| **Verified** | What an authorized test independently established |

`AUTHORITY.lock` records observed/declared authority with explicit confidence and
coverage state — **not** an assertion of every effective runtime permission.

## Claims boundary

authdiff **does**:

- Inventory supported agent-related components and configuration
- Identify declared or potential capabilities
- Find risky patterns with deterministic rules
- Preserve evidence that explains why a finding exists
- Detect changes against `AUTHORITY.lock`
- Export Authority SBOM / draft Agent Authority Manifests
- Produce outputs for developers, reviewers, and CI

authdiff **does not**:

- Prove a component is safe or certify skills / MCP servers
- Sandbox agents or replace host IAM
- Prove exploitability merely because a capability exists
- Guarantee complete discovery of all agent-related authority
- Establish EFFECTIVE or VERIFIED authority from a passive scan alone
- Let an AI agent approve policy or promote claims to `CONFIRMED` without evidence IDs

A clean scan means: **nothing risky was detected in the supported subset**, with
coverage gaps listed. It is never a clearance.

---

## Hybrid responsibility

| Role | Responsibility |
| --- | --- |
| Scanner + adapters | Observable facts, parsing, hashes, inventory |
| Deterministic rules | Reproducible findings + explicit uncertainty |
| Authority engine | Normalize, lock, diff, classify changes |
| AI agent (optional) | Explain evidence, propose remediation |
| Human reviewer | Accept risk, approve authority, own policy |

Deterministic tooling is the source of truth. AI is an optional explainer.

---

## Success metrics (what we optimize)

| Dimension | Metric |
| --- | --- |
| Activation | Time to first meaningful authority map &lt; 2 minutes |
| Activation | Time to first CI integration &lt; 10 minutes |
| Quality | Gated findings always cite evidence references |
| Quality | Independent HIGH/CRITICAL precision ≥ 90% (aspiration; measure via pilots) |
| Coverage | Every scan exposes unsupported / unparsed surfaces when applicable |
| Coverage | Authority-change coverage: % of known authority-bearing changes detected |
| Approval | Approval usefulness: authority diffs that cause least-privilege change, reject, or explicit accept |
| Trust | Zero `CONFIRMED` without independent evidence IDs |
| UX | Default PR comment ≤ 12 lines |
| Security | Zero target code execution during passive inspection |
| Adoption | Independent orgs using the gate; retention after 30 days |

Do **not** optimize for stars, rule count, or number of output files.

**Verdict honesty:** `NO-GATED-FINDINGS` is not the same as “no authority changed.”
When coverage is incomplete, reports must say authority could not be established.

---

## Deferred (intentionally)

Local web viewer, MCP audit server, marketplace / certification, SaaS dashboard,
AgentSecBench-as-product-proof, and runtime capability firewalls are **out of
the current commitment**. See [`ROADMAP.md`](ROADMAP.md) and
[`archive/RADICAL-ALTERNATIVES.md`](archive/RADICAL-ALTERNATIVES.md).

---

## Related contracts

| Doc | Contract |
| --- | --- |
| [`ROADMAP.md`](ROADMAP.md) | 30/90-day plan + success metrics |
| [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) | Lock semantics, identity, diff classes |
| [`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md) | Adapter maturity / unknowns |
| [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md) | Evidence honesty + chain of custody |
| [`TRUST-AND-SAFETY.md`](TRUST-AND-SAFETY.md) | Audit-process trust requirements |
| [`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md) | External validation procedure |
| [`AGENT-AUTHORITY-MANIFEST.md`](AGENT-AUTHORITY-MANIFEST.md) | Manifest + Authority SBOM |
| [`adapters/`](adapters/) | Per-surface maturity specs |
| [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md) | CI gate + trusted policy |
| [`../schemas/authority-lock.schema.json`](../schemas/authority-lock.schema.json) | Machine schema |
