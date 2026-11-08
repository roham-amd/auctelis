# Module — Agent host security

Assess the **host** that loads skills, MCP servers, hooks, plugins, and subagents.
A component’s risk depends on host tool exposure, automatic approvals, process
identity, credential storage, and inter-extension communication.

## Capability checklist

| Capability | Host question | Evidence class |
| --- | --- | --- |
| Tools exposed | Which tools are available to the agent without extra approval? | HOST_CONFIGURATION |
| Auto-approve | What actions skip human confirmation? | HOST_CONFIGURATION |
| Process identity | What OS user / service principal runs the agent? | HOST_CONFIGURATION / RUNTIME |
| Credential storage | Where are API keys, OAuth tokens, and vault refs held? | HOST_CONFIGURATION |
| Hook enforcement | Are hooks mandatory, optional, or bypassable? | HOST_CONFIGURATION |
| Extension isolation | Can plugins/skills observe each other’s context? | HOST_CONFIGURATION |
| Restart persistence | What survives agent restart (memory, hooks, sessions)? | HOST_CONFIGURATION / RUNTIME |
| Network egress | What destinations can the host reach by default? | HOST_CONFIGURATION / RUNTIME |

## Required findings discipline

- Never equate repository configuration with effective host policy.
- Mark host permissions `NOT VERIFIED` unless independently evidenced.
- Pair every high-severity component finding with host-control status.

## Common failure modes

1. Skill marked “read-only” while host auto-approves shell tools.
2. MCP registration reviewed in source while a different binary runs on the host.
3. Hooks mutate arguments after user approval without integrity binding.
4. Shared chat/memory across tenants or projects.
