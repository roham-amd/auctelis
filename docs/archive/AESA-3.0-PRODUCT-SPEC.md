# AESA 3.0 Product Specification

**Status:** Normative methodology for 3.0.x; product experience updated in **3.1.0** (authdiff / `aesa scan`)  
**Date:** 2026-11-04  
**Supersedes (positioning):** AESA Gate notes in 2.3.x (`docs/AUTHDIFF-GATE.md` is the short Guard primer)

**3.1 companion docs (authoritative for Guard UX):** [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md), [`GUARD-SCAN.md`](GUARD-SCAN.md), [`CLI-REFERENCE.md`](CLI-REFERENCE.md), [`SECURITY-RULES.md`](SECURITY-RULES.md), [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md), [`MIGRATION-3.1.md`](MIGRATION-3.1.md).

## 1. Product identity

| Field | Value |
| --- | --- |
| Name | AESA |
| Expanded | Agent Ecosystem Security Assessment |
| Tagline | Evidence-first security for AI-agent ecosystems |
| Delivery | Local-first CLI · AI skill · CI Action |
| Assurance claim | Structured evidence and coverage — **not** certification |

**One-line job:** Discover agent components and trust relationships, establish what they can do with evidence, and prioritize what to fix or verify first.

### Non-goals (unchanged)

- Automated vulnerability scanner / exploit runner
- Runtime malware detonation sandbox
- Marketplace “certified secure” badge
- Compliance certification authority
- Replacement for host IAM, network controls, or risk acceptance

## 2. Architecture

```text
User interfaces
  CLI (`authdiff`) · Cursor/Claude skill · GitHub Action · (later) MCP assist

Audit orchestrator
  Scope · Profiles (quick|standard|deployment) · Stage tracking · Authz boundaries

Deterministic engine
  Discovery adapters · Bounded I/O · Hashes · Validation · Diff · Graph seed · SARIF

AI reasoning engine (external agent)
  Threat modeling · Prompt analysis · Attack paths · Severity/confidence proposals

Shared model
  Component IDs · Evidence registry · Trust graph · Findings · Coverage · Confidence

Deliverables
  Markdown context · Inventory JSON · Graph · Report JSON · Baseline · SARIF
```

### Responsibility split

| Responsibility | Owner |
| --- | --- |
| Pin revision, walk tree, parse manifests, hashes | Deterministic tool |
| Structural / semantic validation, diff, SARIF | Deterministic tool |
| Relationship hints from configs | Tool (+ agent refine) |
| Vulnerability interpretation, attack-path reasoning | AI agent |
| Scope authorization, production acceptance | Human |

**Principle:** Machines establish what can be established mechanically. AI investigates contextual risk. Humans decide acceptability.

## 3. CLI contract

Install: `cd tools && uv sync --locked` → console script `authdiff` (via `.venv` / `uv run`).

> **3.5 note:** The live primary path is Authority Diff —
> `aesa doctor` / `aesa vet` / `aesa scan` / `aesa init-gate`. The `aesa audit`
> profiles below remain supported for agent handoff packages.

### Primary command (historical 3.0)

```bash
aesa audit PATH [--profile quick|standard|deployment] [-o OUT_DIR]
```

| Profile | Deterministic work | Agent handoff package | Typical use |
| --- | --- | --- | --- |
| `quick` | Inventory, coverage, graph seed, console summary | Minimal `audit-context.md` | First look / under 10 minutes |
| `standard` | Same + module selection hints + stage checklist | Full handoff for deep review | Default assessment |
| `deployment` | Same as standard + deployment evidence worksheet | Host / data-sensitivity gates | Production suitability |

`aesa preflight` remains as an alias of `aesa audit --profile quick` for 2.3 compatibility.

### Supporting commands (stable)

| Command | Purpose |
| --- | --- |
| `aesa inventory PATH` | JSON-only passive discovery |
| `aesa validate report\|graph` | Schema + semantic checks |
| `aesa graph paths` | Path search on typed graph |
| `aesa diff report\|graph` | Assessment / graph comparison |
| `aesa export sarif` | SARIF 2.1.0 for file-backed findings |
| `aesa verify digest\|manifest` | SHA-256 helpers (**manifest builds** a digest list; does not yet verify an input manifest against a tree) |
| `aesa corpus run` | Deterministic tooling corpus |
| `aesa benchmark run` | Agent-detection benchmark harness (fixtures + scoring stubs) |
| `aesa build all` | Schema sync, version gates, link check, monolith parity |

### Default outputs (`OUT_DIR`, default `<PATH>/authdiff-out`)

| File | Contents |
| --- | --- |
| `inventory.json` | Components, coverage matrix, parser events, limits |
| `ecosystem-graph.json` | Structural graph seed (not attack-path proof) |
| `audit-context.md` | Agent handoff |
| `preflight-summary.md` / `audit-summary.md` | Human console twin |
| `profile.json` | Selected profile + stage expectations |
| `deployment-worksheet.md` | Only for `deployment` profile |

### Safety defaults

- Read-only target inspection
- No target script execution, dependency install, MCP invoke, or operational network
- Shared bounded traversal: `max_files`, `max_depth`, `max_file_bytes`; no symlink follow
- Truncation and skip events must appear in `parser_events` (zero silent truncation)

## 4. Inventory and adapter architecture

### Shared I/O

All adapters consume a pre-walked file list from `aesa.inventory.io.iter_repo_files` and read via `safe_read_text` (path containment, depth, size, symlink refusal).

### Adapter maturity

| Level | Meaning |
| --- | --- |
| `SUPPORTED` | Deterministic discovery of common layouts; still not runtime proof |
| `PARTIAL` | Heuristic / host-subset; gaps expected |
| `MANUAL_ONLY` | Procedure/modules only |
| `UNSUPPORTED` | Explicitly out of passive tooling |

### Adapter matrix (3.0.0)

| Family | Adapter id | Maturity |
| --- | --- | --- |
| Skill | `skill_md` | SUPPORTED |
| MCP client config | `mcp_config` | PARTIAL |
| A2A Agent Card | `a2a_agent_card` | PARTIAL |
| Instruction rules | `instruction_rules` | SUPPORTED |
| Hook | `hooks` | PARTIAL |
| Plugin | `plugins` | PARTIAL |
| Subagent | `subagents` | PARTIAL |
| Automation | `automations` | PARTIAL |
| CI / workflow authority | `github_workflows` | PARTIAL |
| Host effective permissions | — | MANUAL_ONLY |
| Runtime behavior | — | UNSUPPORTED |
| Publisher / provenance | digest helpers only | MANUAL_ONLY |

Stable component ids: `C-NNN` assigned in discovery order within a single inventory run.

Inventory JSON version field: `aesa_inventory_version` (3.0.0 bumps to `"0.3.0"`).

## 5. Evidence model

Report schema remains **`audit_version: "1.0"`** until a breaking contract change is required.

Evidence classes (normative):

`SOURCE_STATIC` · `ARTIFACT` · `PROVENANCE` · `HOST_CONFIGURATION` · `RUNTIME` · `EXTERNAL_INTELLIGENCE` · `USER_ASSERTION`

Verification statuses for claims/findings:

`OBSERVED` · `CONFIRMED` · `POTENTIAL` · `NOT VERIFIED` · `NOT ASSESSED` · `NOT APPLICABLE`

Rules:

1. `CONFIRMED` high/critical findings require evidence ids (enforced semantically).
2. Source observation ≠ host enforcement ≠ runtime behavior.
3. Evidence must not copy raw secrets; redact by default.
4. Prefer `INSUFFICIENT EVIDENCE` over unsupported assurance.

## 6. Repository structure (3.0)

```text
authdiff/
├── VERSION                          # aesa_product
├── canonical/                       # schemas, versions.json, prompt manifest
├── tools/authdiff/                      # CLI + engines
│   ├── audit.py                     # unified audit orchestrator
│   ├── preflight.py                 # shared discovery writers (used by audit)
│   ├── inventory/                   # limits, io, coverage, adapters/
│   ├── export/ · graph/ · corpus/ · supply_chain/
│   └── benchmark/                   # agent detection harness
├── skills/                          # native AI skill entry
├── prompts/ · modules/              # methodology (procedure v1.0)
├── schemas/                         # published contracts
├── tests/corpus/                    # tooling regression
├── tests/benchmark/                 # detection quality fixtures
├── .github/workflows/               # kit CI + example consumer gate
├── .github/actions/authdiff-gate/       # reusable composite Action
└── docs/
    ├── AESA-3.0-PRODUCT-SPEC.md     # this document
    ├── AUTHDIFF-GATE.md                 # short primer
    ├── usage.md
    └── architecture/
```

## 7. Profiles ↔ nine-stage methodology

Procedure stages 0–8 remain under `archive/methodology/prompts/`. Profiles select **how far** the orchestrator pushes the operator/agent:

| Stage | Quick | Standard | Deployment |
| --- | --- | --- | --- |
| 0 Scope / capability | Required | Required | Required |
| 1–2 Discovery / candidates | Tool-led | Tool-led | Tool-led |
| 3–4 Component deep audit | Optional | Expected for priority set | Expected |
| 5 Artifact / supply chain | Optional | As evidence allows | Expected where artifacts used |
| 6 Host / integration | Manual note | Expected questions | Required worksheet |
| 7 Cross-component paths | Hint only | Expected when multi-component | Expected |
| 8 Runtime | Out of scope unless authorized | Same | Same |
| Production suitability | Not claimed | Not claimed without host evidence | Explicit gate section |

## 8. Distribution

| Channel | 3.0.0 expectation |
| --- | --- |
| `uv sync --locked` from `tools/` | Required |
| `skills/authdiff-auditor-compat` | Required entry skill |
| Consumer GitHub Action (composite) | Ships under `.github/actions/authdiff-gate` |
| PyPI publish | Optional follow-up |
| Hosted web app / marketplace | Deferred |

## 9. Thirty-day implementation backlog (tracked)

| Days | Deliverable | 3.0.0 status |
| --- | --- | --- |
| 1–3 | Release consistency | Done in 2.3 + 3.0 version bump |
| 4–8 | Shared bounded I/O + stable ids | Done |
| 9–14 | Adapters: hooks/plugins/subagents/automations/CI | Done (PARTIAL where noted) |
| 15–19 | `aesa audit` + profiles | **This release** |
| 20–23 | Skill + staged module loading docs | Done + updated for `audit` |
| 24–27 | Consumer Action + baseline/diff recipe | **This release** |
| 28–30 | Benchmark scaffold + docs/examples | **This release** |

## 10. Success metrics (targets, not measured yet)

| Metric | Target |
| --- | --- |
| Install → useful inventory | < 5 minutes |
| First evidence-backed observation path | < 10 minutes |
| CONFIRMED findings with evidence refs | 100% |
| Adapter recall on deterministic fixtures | ≥ 95% |
| Silent inventory truncation | 0 |
| Passive target-code execution | 0 |
| Critical/high precision on reviewed benchmark cases | ≥ 90% (when benchmark populated) |

## 11. Versioning

| Stream | 3.1.0 value |
| --- | --- |
| `VERSION` / `aesa_product` | `3.1.0` |
| Audit procedure | `1.0` |
| Report / graph / manifest schemas | `1.0` |
| `authdiff` package | `0.4.0` |
| Tooling corpus | `0.3.0` |
| AgentSecBench | `0.2.0` |

Breaking product UX (unified `audit`, Assessment naming, Action packaging) justifies the major version. Report JSON contract stays 1.0.
