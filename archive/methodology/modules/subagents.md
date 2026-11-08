# Module: Subagents and Multi-Agent Systems

**AESA module ID:** `SUBAGENTS`  
**Procedure reference:** Section 10.5 of `prompts/02-modules.md` (core: `prompts/01-core-prompt.md`)
**Applies when:** component type is `Subagent`, `Agent Definition`, multi-agent orchestrator, or parent/child Agent delegation is present.

A child Agent must **not** automatically inherit all authority of its parent. Inter-Agent messages and summaries are untrusted until authenticated and authorized.

## Inspection surfaces

- Agent identity, publisher/source, parent-child relationship
- Session identity and task ownership
- Sender authentication / message integrity / provenance
- Recipient validation and delegation policy
- Delegated credentials and inherited tools
- Environment variables, filesystem/network access, model/provider access
- Shared memory, token forwarding, privilege reduction
- Nested delegation, recursion, fan-out, concurrency
- Timeouts, cancellation, budgets, error propagation, result validation
- Cross-session messaging and tenant isolation

## Checklist

- [ ] Exact Subagent identity and source/ref recorded
- [ ] Parent/child relationship and task ownership mapped
- [ ] Message authentication / integrity / replay protections reviewed
- [ ] Capability inheritance vs privilege reduction reviewed
- [ ] Delegated credentials / token forwarding bounded?
- [ ] Shared memory and cross-session contamination assessed
- [ ] Recursion / fan-out / budget / cancellation bounded?
- [ ] Result validation before privileged parent actions assessed
- [ ] Tenant isolation enforced at data operation (not only in prompts)
- [ ] Spoofed summaries / untrusted task results treated as injection surfaces

## Cross-component gates (typical)

- X-G02 Delegated identities and credentials bounded
- X-G03 Permission inheritance and privilege reduction reviewed
- X-G09 Shared memory, session, and tenant boundaries reviewed
- X-G12 Cascading failure, recursion, fan-out, and cancellation bounded

## Passive-audit constraints

- Do not launch Subagents or invoke inter-Agent messaging against production.
- Runtime privilege inheritance remains `NOT VERIFIED` without host/config or staging evidence.
