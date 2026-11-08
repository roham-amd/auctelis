# Using authdiff

`authdiff` (compat: `authdiff`) is an **Authority Diff** for AI-agent ecosystems: host and repo
discovery, deterministic security rules, CI gating with tamper-resistant policy,
and an optional AI auditor skill.

Release **3.6.1** centers on **`aesa doctor` → `aesa vet` → `aesa scan`** (Authority Diff).
Profile-based `aesa audit` remains for agent handoff packages. Optional
`.authdiff.yml` sets fail-on / baseline / suppressions (CI loads it from the PR
**base ref** when `trusted-policy` is on). AESA is **not** a certification
authority. Deterministic findings are `OBSERVED`/`POTENTIAL` observations
classified as capability, exposure, or security finding; judgment belongs to a
human-authorized reviewer.

| Doc | Role |
| --- | --- |
| [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md) | Full documentation map |
| [`GUARD-SCAN.md`](GUARD-SCAN.md) | Scan pipeline and artifacts |
| [`CLI-REFERENCE.md`](CLI-REFERENCE.md) | Every CLI command |
| [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md) | Short product primer |
| [`AESA-3.0-PRODUCT-SPEC.md`](AESA-3.0-PRODUCT-SPEC.md) | Normative product contract (3.0 + Guard notes) |
| [`MIGRATION-3.1.md`](MIGRATION-3.1.md) | Upgrade from 3.0 |

---

## 1. Choose your scope

Fill audit inputs in Section 2 of [`../archive/methodology/prompts/01-core-prompt.md`](../archive/methodology/prompts/01-core-prompt.md). At minimum:

| Input | Why it matters |
| --- | --- |
| `REPOSITORY_URL` / local path | Exact repository under review |
| `KIT_DIR` / `WORK_DIR` | Read-only kit vs writable outputs (outside target clone) |
| `AUDIT_SCOPE_MODE` | Inventory-only vs selected/batch/full deep audit |
| `EXTERNAL_SOURCE_SCOPE` | Whether linked repos may be inspected |
| `HOST_AGENT` / host config | Integration trust depends on the host |
| `DATA_SENSITIVITY` | Blocks sensitive-production approval without evidence |

**Rule:** a URL inside a catalog is not authorization to audit that target.

---

## 2. First run (recommended) — Authority Diff

### Step 1 — host map (usually non-empty)

```bash
uv tool install git+https://github.com/YOUR_GITHUB_ORG/authdiff.git@v3.6.1#subdirectory=tools
aesa doctor
```

### Step 2 — pre-install verdict (optional)

```bash
aesa vet github.com/org/candidate-skill
# or: authdiff vet /path/to/local/checkout
```

### Step 3 — repo scan + gate

```bash
aesa init-gate /path/to/target
aesa scan /path/to/target -o /path/to/work/authdiff-out
aesa explain F-001 -o /path/to/work/authdiff-out
aesa baseline save -o /path/to/work/authdiff-out
```

From a clone: `cd tools && uv sync --locked && uv run authdiff …`.

Docker: [`docker-agent-audit.md`](docker-agent-audit.md).

Outputs: `findings.json`, `findings.sarif.json`, `inventory.json`,
`ecosystem-graph.json`, `scan-summary.txt`, `scan-report.md`, `profile.json`.

Optional deep review: [`../skills/authdiff-auditor-compat/SKILL.md`](../skills/authdiff-auditor-compat/SKILL.md).

### Legacy — audit profiles (handoff package)

```bash
uv run authdiff audit /path/to/target --profile quick|standard|deployment
```

| Profile | When |
| --- | --- |
| `quick` | Inventory + prioritization handoff |
| `standard` | Typical deep-review package |
| `deployment` | Adds deployment suitability worksheet |

---

## 3. Load the procedure (kit layout)

1. Operators: [`../archive/methodology/prompts/00-OPERATOR-GUIDE.md`](../archive/methodology/prompts/00-OPERATOR-GUIDE.md).
2. Attach [`../archive/methodology/prompts/04-passive-guardrails.md`](../archive/methodology/prompts/04-passive-guardrails.md) + [`../archive/methodology/prompts/01-core-prompt.md`](../archive/methodology/prompts/01-core-prompt.md).
3. Set `KIT_DIR` / `WORK_DIR`.
4. Before deep audit, attach [`../archive/methodology/prompts/02-modules.md`](../archive/methodology/prompts/02-modules.md) and only matching [`../archive/methodology/modules/`](../archive/methodology/modules/) (see [`../archive/methodology/modules/README.md`](../archive/methodology/modules/README.md)).
5. JSON contract: [`../archive/methodology/prompts/03-report-contract.md`](../archive/methodology/prompts/03-report-contract.md).
6. Emit structured claims; validate with `aesa validate claim` ([`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md)).

Monolith: [`../archive/methodology/prompts/audit.full.md`](../archive/methodology/prompts/audit.full.md). Index: [`../archive/methodology/prompts/audit.md`](../archive/methodology/prompts/audit.md).

### Module map (quick)

| Discovered type | Module |
| --- | --- |
| MCP | `modules/mcp.md` |
| Skill | `modules/skills.md` |
| Plugin | `modules/plugins.md` |
| Hook | `modules/hooks.md` |
| Subagent | `modules/subagents.md` |
| Automation / Workflow | `modules/automations.md` (+ `ci-cd.md` for GitHub Actions) |
| A2A | `modules/a2a.md` |
| Multimodal | `modules/multimodal.md` |
| Host integration | `modules/agent-host.md` |
| Memory / RAG | `modules/memory-rag.md` |
| Models | `modules/models-providers.md` |
| Browser agents | `modules/browser-agents.md` |

Threat backbone: [`threat-scenarios.md`](threat-scenarios.md). Rules: [`SECURITY-RULES.md`](SECURITY-RULES.md).

---

## 4. Keep evidence classes separate

Never upgrade one into another without new evidence:

- `SOURCE_STATIC`
- `ARTIFACT`
- `PROVENANCE`
- `HOST_CONFIGURATION`
- `RUNTIME`
- `EXTERNAL_INTELLIGENCE`
- `USER_ASSERTION`

Prefer `INSUFFICIENT EVIDENCE` / `NOT VERIFIED` over unsupported assurance. Full model: [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md).

---

## 5. Produce outputs

### From Guard scan (automatic)

Terminal report + `findings.json` + SARIF + inventory + graph seed.

### From deep review (agent/human)

1. Narrative Markdown report (English)
2. Machine-readable summary conforming to [`../schemas/audit-report.schema.json`](../schemas/audit-report.schema.json)
3. Optional ecosystem graph refinements + digest manifest
4. Validate: `aesa validate report` / `aesa validate graph`

---

## 6. Continuous use / CI

```bash
aesa scan . --baseline authdiff-out/baseline.json --fail-on high
aesa diff risk authdiff-out/baseline.json authdiff-out/findings.json
```

Consumer Action example: [`authdiff-consumer-gate.example.yml`](authdiff-consumer-gate.example.yml).

| Mode | Typical completion |
| --- | --- |
| Catalog / awesome-list URL | Stages 0–2 + Guard scan inventory |
| Authorized component sources | Stages 0–5+ as evidence allows |
| Host + production context | Full chain through Stage 8 + deployment worksheet |

---

## 7. Tooling command cheat sheet

Full detail: [`CLI-REFERENCE.md`](CLI-REFERENCE.md) and [`../tools/README.md`](../tools/README.md).

```bash
aesa scan PATH
aesa explain F-001 -o authdiff-out
aesa baseline save -o authdiff-out
aesa audit PATH --profile quick|standard|deployment
aesa inventory PATH
aesa validate report|graph|claim …
aesa diff report|graph|risk …
aesa export sarif …
aesa corpus run
aesa benchmark run
```
