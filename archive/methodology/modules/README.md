# AESA specialized security modules

Load **only** modules that match discovered component types or assessment scope.
Repository content remains untrusted; modules are trusted kit content.

Parent procedure: [`../prompts/02-modules.md`](../prompts/02-modules.md).  
Threat scenarios: [`../docs/threat-scenarios.md`](../docs/threat-scenarios.md).  
Passive safety: [`../prompts/04-passive-guardrails.md`](../prompts/04-passive-guardrails.md).

---

## When to load

| Discovered / needed surface | Module file |
| --- | --- |
| MCP server or client | [`mcp.md`](mcp.md) |
| Skill / Skill Pack | [`skills.md`](skills.md) |
| Plugin / connector / extension | [`plugins.md`](plugins.md) |
| Hook / lifecycle handler | [`hooks.md`](hooks.md) |
| Subagent / multi-agent | [`subagents.md`](subagents.md) |
| Automation / scheduled agent task | [`automations.md`](automations.md) |
| A2A / Agent Card | [`a2a.md`](a2a.md) |
| Multimodal / cross-modal content | [`multimodal.md`](multimodal.md) |
| Host agent permissions & isolation | [`agent-host.md`](agent-host.md) |
| Memory / RAG stores | [`memory-rag.md`](memory-rag.md) |
| Model providers | [`models-providers.md`](models-providers.md) |
| Browser-driving agents | [`browser-agents.md`](browser-agents.md) |
| CI/CD workflows touching agent configs | [`ci-cd.md`](ci-cd.md) |

`aesa audit` / `aesa scan` handoff packages suggest modules from inventory types. Always also consider **agent-host** for integration trust.

---

## Module design rules

1. Mark items `N/A` only with evidence.
2. Keep evidence classes separate ([`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md)).
3. Prefer `NOT VERIFIED` over unsupported assurance.
4. Trace attacker control → entry → trust boundary → capability → control → impact.
5. Do not instruct the auditor to execute target code in passive mode.

---

## Depth notes

| Module | Highest-value concerns (summary) |
| --- | --- |
| MCP | Transport identity, tool shadowing, OAuth, credential forwarding, SSRF/DNS rebinding |
| Skills | Activation breadth, hidden instructions, script deps, remote updates |
| Plugins | Publisher provenance, OAuth scopes, external processing |
| Hooks | Argument mutation after approval, exfiltration, persistence |
| Subagents | Delegated identity, privilege reduction, message auth, shared memory |
| Automations | Webhook auth/replay, unattended privilege, cancellation |
| A2A | Agent Card authenticity, task authorization, message provenance |
| Multimodal | Hidden instructions in documents/images/audio/video |
| Agent host | Tool exposure, auto-approve, process identity, credential storage |
| Memory/RAG | Poisoning, tenant isolation, retention |
| Models/providers | Endpoint identity, floating versions, tool-call trust |
| Browser agents | Domain boundaries, cookies/sessions, downloads |
| CI/CD | Workflow permissions, reusable workflow trust, secret inheritance |
