# authdiff coverage matrix

Authoritative runtime source: `tools/authdiff/inventory/coverage.py` → `ADAPTER_COVERAGE`
(emitted on every scan as `inventory.json` → `coverage.adapter_matrix`).

Keep this document aligned when adapters change. Maturity values:

| Maturity | Meaning |
| --- | --- |
| `SUPPORTED` | Deterministic discovery is production-quality for common layouts |
| `PARTIAL` | Discovery exists; format gaps or host binding remain |
| `MANUAL_ONLY` | Assessment module / checklist only — no dedicated adapter |
| `UNSUPPORTED` | Out of scope for passive Guard |

## Automated discovery vs modules

| Surface | Automated discovery | Maturity | Next improvement |
| --- | --- | --- | --- |
| Skills | `skill_md` | SUPPORTED | More package formats and dependency resolution |
| MCP client registration | `mcp_config` | PARTIAL | Broader registration formats; server-source linking |
| MCP server source | `mcp_server_source` | PARTIAL | Tool authz verification |
| A2A | `a2a_agent_card` | PARTIAL | Message authentication and trust relationships |
| Instruction rules | `instruction_rules` | SUPPORTED | Host-specific rule packs |
| Hooks | `hooks` | PARTIAL | Execution-chain analysis |
| Plugins | `plugins` | PARTIAL | Publisher and artifact provenance |
| Subagents | `subagents` | PARTIAL | Delegated authority relationships |
| Automations | `automations` | PARTIAL | Trigger and execution identity coverage |
| CI / GitHub Actions | `github_workflows` | PARTIAL | Reusable workflow and identity analysis |
| Agent host profiles | `host_profiles` | PARTIAL | Effective permission evidence |
| Browser agents | — | MANUAL_ONLY | Browser-policy and session-surface discovery |
| Memory / RAG | — | MANUAL_ONLY | Integration and tenant-boundary discovery |
| Model providers | — | MANUAL_ONLY | Endpoint and model configuration discovery |
| Multimodal artifacts | — | MANUAL_ONLY | Artifact inspection adapters |
| Runtime behavior | — | UNSUPPORTED | Isolated opt-in runtime harness |
| Publisher / provenance | digest helpers | MANUAL_ONLY | Signature / SBOM verification |

## Host profile maturity (engineering plan)

| Host | Status |
| --- | --- |
| Cursor | Partial profile |
| Claude Code | Partial profile |
| GitHub Copilot | Manual-only |

## Operator rule

Absence of findings on a `MANUAL_ONLY` or `UNSUPPORTED` family is **not** evidence of safety.
Every scan report lists `NOT VERIFIED` surfaces and manual-only families explicitly.
