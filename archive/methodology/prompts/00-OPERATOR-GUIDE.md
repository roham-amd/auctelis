# Operator guide: AESA Kit (procedure 1.0) + Guard tooling

This guide orients humans who run AESA engagements. Product release **3.5.1**
centers on **authdiff** as an Authority Diff (`aesa doctor` / `aesa vet` /
`aesa scan`); the audit **procedure version remains 1.0**.

Full documentation map: [`../docs/DOCUMENTATION-INDEX.md`](../docs/DOCUMENTATION-INDEX.md).

---

## What is in the kit

| File / path | Role |
| --- | --- |
| `01-core-prompt.md` | Main procedure (stages, inputs, report sections). Give to the audit agent; fill Section 2 inputs. |
| `02-modules.md` | Component-type module summaries. Load **only** what applies. |
| `../modules/*.md` | Deep checklists (MCP, Skill, Plugin, Hook, Subagent, Automation, A2A, Multimodal, Host, Memory, Models, Browser, CI/CD). Index: [`../modules/README.md`](../modules/README.md). |
| `03-report-contract.md` | JSON templates, enums, output files, schema references. |
| `04-passive-guardrails.md` | **Required:** non-execution, anti-injection, `KIT_DIR`/`WORK_DIR`, worker rules. |
| `../schemas/*.json` | Official JSON Schemas. Catalog: [`../schemas/README.md`](../schemas/README.md). |
| `../examples/*` | Sample context, inventory, and summary. |
| `audit.full.md` | Full monolithic procedure (generated; single-file alternative). |
| `../skills/authdiff-auditor-compat/SKILL.md` | Canonical AI auditor skill (Guard-first). |
| `../tools/` | Deterministic CLI (`aesa scan`, validate, corpus, …). |

---

## Difference from generic audit kits

AESA targets **agent ecosystems** (Skills, MCP, Hooks, …), not generic automated repo scanning. Passive audits are **read-only**. A secure environment (VM, restricted egress, no secrets) is still recommended—the prompt is not a technical sandbox.

Guard scan adds **deterministic** security observations. Those observations are not certification.

---

## Environment prerequisites

1. **No secrets** in the agent environment: no SSH keys, cloud credentials, or production env vars.
2. **Restricted egress** if the agent has network access; only hosts allowed in scope.
3. **Read-only kit** — `KIT_DIR` = path to this kit (or a read-only copy). Never clone the audit target into `KIT_DIR`.
4. **Writable `WORK_DIR`** — clones, reports, JSON, and state **outside** the target repo (e.g. `/audit/work`).
5. **GitHub token** read-only only, preferably via a secure integration—never paste tokens in chat.
6. **Guardrails:** the agent must load `04-passive-guardrails.md` at audit start; give subagents **Section 1** verbatim.

---

## Recommended execution steps (Guard-first)

0. **Guard scan (deterministic):**

   ```bash
   cd <AUTHDIFF_KIT>/tools && uv sync --locked
   uv run authdiff scan <TARGET> -o <WORK_DIR>/authdiff-out
   ```

   Read `authdiff-out/scan-summary.txt`, `findings.json`, `inventory.json`.  
   Details: [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md), rules: [`../docs/SECURITY-RULES.md`](../docs/SECURITY-RULES.md).

1. Read this file and [`../docs/usage.md`](../docs/usage.md).
2. Provide `04-passive-guardrails.md` and either:
   - [`../skills/authdiff-auditor-compat/SKILL.md`](../skills/authdiff-auditor-compat/SKILL.md), or
   - `01-core-prompt.md` with Section 2 filled (`REPOSITORY_URL`, `KIT_DIR`, `WORK_DIR`, `AUDIT_SCOPE_MODE`, `EXTERNAL_SOURCE_SCOPE`, `DATA_SENSITIVITY`, host context).
3. Agent completes stages 0–2 (scope, discovery, triage) using scan artifacts when available.
4. **Before Phase 4 deep audit**, attach `02-modules.md` and needed files from `modules/` (always consider `agent-host.md` for integration trust).
5. Require structured claims (`aesa validate claim`) before promoting status to `CONFIRMED` — [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md).
6. Narrative report per Section 21; JSON per `03-report-contract.md` and the schema; `aesa validate report`.
7. Optional: `aesa baseline save` for continuous reassessment / CI.

For large catalogs: batch with `COMPONENT_BATCH_SIZE` and `audit-state.json` across sessions.

Docker path: [`../docs/docker-agent-audit.md`](../docs/docker-agent-audit.md).

---

## Module map

| Discovered | Load |
| --- | --- |
| MCP Server / Client | `modules/mcp.md` |
| Skill / Skill Pack | `modules/skills.md` |
| Plugin / Connector | `modules/plugins.md` |
| Hook | `modules/hooks.md` |
| Subagent | `modules/subagents.md` |
| Automation / scheduled workflow | `modules/automations.md` |
| A2A / Agent Card | `modules/a2a.md` |
| Multimodal | `modules/multimodal.md` |
| Host agent / IDE permissions | `modules/agent-host.md` |
| Memory / RAG | `modules/memory-rag.md` |
| Models / providers | `modules/models-providers.md` |
| Browser agents | `modules/browser-agents.md` |
| CI/CD workflows | `modules/ci-cd.md` |
| Rule packs / other | Sections in `02-modules.md` |

Threat scenarios: [`../docs/threat-scenarios.md`](../docs/threat-scenarios.md).

---

## Honest limitations

- AESA is **not** an automated scanner that proves systems are safe, a sandbox, or a penetration test.
- Default report `score` is **null**; do not invent numeric scores.
- `recommend_production_use` is true only when production gates actually pass.
- A catalog link is **not** authorization to audit an external repo.
- Zero Guard findings ≠ safe (coverage may be incomplete).
- AgentSecBench fixture pass rates are **not** LLM detection accuracy.

---

## Four separate questions

1. **Discovery** — What does the repo contain or reference?
2. **Component trust** — Is each in-scope source/artifact acceptable?
3. **Integration trust** — Is host connection bounded by identity and permissions?
4. **Production suitability** — Is the deployment acceptable for declared data sensitivity?

A positive answer to one does not imply the others.
