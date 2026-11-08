# Migration to AESA 2.0.0

Baseline repository commit before engineering transition: `82e3ec8328a4a4e54b7604fd7f09dafd041fbb74` (AESA **1.1.0**, procedure **1.0**).

## What changed

| Area | 1.1.x | 2.0.0 |
| --- | --- | --- |
| Role | Prompt kit + schemas only | Hybrid: prompt kit **plus** deterministic tooling |
| Schema source | Edited under `schemas/` | Canonical copy under `canonical/schemas/`; `schemas/` synced by build |
| Validation | Structural JSON Schema only | Schema + **semantic** referential integrity checks (`aesa validate report`) |
| Inventory | Manual discovery | Optional passive collector (`aesa inventory`) — partial adapters |
| Graph | Narrative / booleans in report | Typed `schemas/ecosystem-graph.schema.json` (pilot) |
| Control mapping | Prose references | Starter control pack under `control-packs/` (partial AISVS) |
| Tests | None | Corpus + CI (`aesa corpus run`, GitHub Actions) |

## Breaking changes

- **None** to audit report JSON `audit_version: "1.0"` contract in this release. Semantic validation may reject reports that were previously accepted structurally but contained dangling references.
- Product version **2.0.0** reflects new tooling and governance — not a procedure major bump (procedure remains **1.0** until enum/workflow changes ship).

## Operator migration

1. Install tooling: `cd tools && uv sync --locked`.
2. Before publishing JSON summaries, run `aesa validate report path/to/security-audit-summary.json`.
3. Optionally generate inventory: `aesa inventory /path/to/target-repo -o repository-inventory.json` and reconcile with manual discovery.
4. Attach new modules when applicable: `modules/a2a.md`, `modules/multimodal.md`.
5. When citing controls, reference control pack version `owasp-aisvs/1.0-starter` — not full AISVS compliance.

## Contributor migration

- Edit **`canonical/schemas/audit-report.schema.json`**, then `aesa build schemas`.
- Do not hand-edit generated schema aliases unless fixing a release emergency (then backport to canonical).
- Prompt kit canonical composition: `canonical/prompt-kit.manifest.json`.
- Run `aesa build all` and `aesa corpus run` before opening PRs.

## Later releases (see also 3.0)

- **2.1+:** `aesa graph paths` (pilot path search), monolith generator, A2A/rules inventory.
- **2.2+:** SARIF export, audit diff, digest manifests.
- **2.3+:** `aesa preflight`, expanded adapters, native skills.
- **3.0.0:** `aesa audit --profile …`, consumer Action, benchmark scaffold — [`AESA-3.0-PRODUCT-SPEC.md`](AESA-3.0-PRODUCT-SPEC.md).

## Not yet available (do not claim)

- Full AISVS 191-requirement crosswalk (R-007 remainder)
- Full automated attack-path proof engine (path search is heuristic on typed graphs)
- SBOM/signature/provenance verifiers beyond digest helpers (R-008)
- Runtime staging harness (R-009)
- LLM procedure benchmark scores (tooling corpus + benchmark inventory stubs only; no model runner yet)
