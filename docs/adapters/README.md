# Adapter maturity specs

Each adapter states what it **can** and **cannot** establish. Support means
reliable, tested evidence for a stated subset — not “we parsed one file.”

Authority layers used below: **Declared / Configured / Effective / Verified**.
Passive authdiff establishes Declared/Configured only unless noted.

| Priority | Surface | Adapter | Maturity | Spec |
| --- | --- | --- | --- | --- |
| 1 | MCP clients | `mcp_config` | PARTIAL | [mcp-clients.md](mcp-clients.md) |
| 2 | MCP server source | `mcp_server_source` | PARTIAL | [mcp-servers.md](mcp-servers.md) |
| 3 | Skills | `skill_md` | SUPPORTED | [skills.md](skills.md) |
| 4 | Hooks | `hooks` / `claude_settings` | PARTIAL | [hooks.md](hooks.md) |
| 5 | Plugins | `plugins` | PARTIAL | [plugins.md](plugins.md) |
| 6 | Subagents | `subagents` | PARTIAL | [subagents.md](subagents.md) |
| 7 | Automations | `automations` | PARTIAL | [automations.md](automations.md) |
| 8 | Host configuration | `host_profiles` | PARTIAL | [host.md](host.md) |
| 9 | CI/CD | `github_workflows` | PARTIAL | [ci.md](ci.md) |
| 10 | Memory/RAG | — | MANUAL_ONLY | checklist only |

Runtime behavior remains **UNSUPPORTED** in passive mode.
