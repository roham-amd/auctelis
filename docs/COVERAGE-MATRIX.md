# authdiff coverage matrix

Authoritative runtime source: `tools/authdiff/inventory/coverage.py` → `ADAPTER_COVERAGE`  
Emitted on every scan as `inventory.json` / `findings.json` → `coverage.adapter_matrix`.

A clean scan means **nothing risky was detected in the supported subset**, not
that the ecosystem was comprehensively examined. Coverage is a first-class
product output.

**Authority layers:** Declared → Configured → Effective → Verified. Passive
authdiff establishes Declared/Configured only. See [`adapters/`](adapters/) for
per-surface maturity specs and [`TRUST-AND-SAFETY.md`](TRUST-AND-SAFETY.md).

## Maturity labels

| Maturity | Meaning |
| --- | --- |
| `SUPPORTED` | Deterministic discovery is production-quality for common layouts |
| `PARTIAL` | Discovery exists; format gaps or host binding remain |
| `EXPERIMENTAL` | Best-effort; expect misses |
| `MANUAL_ONLY` | Checklist / module only — no dedicated adapter |
| `UNSUPPORTED` | Out of scope for passive authdiff |

## Surface coverage

| Surface | Adapter | Maturity | Make explicit |
| --- | --- | --- | --- |
| Skills | `skill_md` | SUPPORTED | Instructions ≠ executable behavior |
| MCP client registration | `mcp_config` | PARTIAL | Configured capability ≠ server behavior |
| MCP server source | `mcp_server_source` | PARTIAL | Tool authz not verified |
| A2A | `a2a_agent_card` | PARTIAL | Message trust / delegation manual |
| Instruction rules | `instruction_rules` | SUPPORTED | Host packs vary |
| Hooks | `hooks` | PARTIAL | Event + execution context |
| Plugins | `plugins` | PARTIAL | Declared vs host-enforced scope |
| Subagents | `subagents` | PARTIAL | Inherited vs escalated authority |
| Automations | `automations` | PARTIAL | Unattended triggers / credentials |
| CI / GitHub Actions | `github_workflows` | PARTIAL | Untrusted code influencing privileged jobs |
| Host configurations | `host_profiles` | PARTIAL | Inventory ≠ effective host permissions |
| Browser agents | — | MANUAL_ONLY | No dedicated adapter |
| Memory / RAG | — | MANUAL_ONLY | Retention / tenant isolation |
| Model providers | — | MANUAL_ONLY | Data routing / custom endpoints |
| Multimodal artifacts | — | MANUAL_ONLY | No artifact inspection adapters |
| Runtime behavior | — | UNSUPPORTED | Passive mode never executes targets |
| Publisher / provenance | digest helpers | MANUAL_ONLY | Signature / SBOM not full product |

## Host profile maturity

| Host | Status |
| --- | --- |
| Cursor | Partial profile |
| Claude Code | Partial profile |
| Codex | Partial profile |
| VS Code / Copilot markers | Partial / manual |

## Operator rule

For every surface, the product should make visible:

1. Was it discovered?
2. Was it parsed?
3. Which adapter / maturity applied?
4. Which controls were evaluated?
5. What remained `NOT VERIFIED` / `NOT ASSESSED`?

Absence of findings on `MANUAL_ONLY` or `UNSUPPORTED` families is **not**
evidence of safety. Unparsed agent configs fail closed.
