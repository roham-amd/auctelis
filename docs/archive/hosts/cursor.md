# Cursor host profile

**Support:** PARTIAL  
**CLI:** `aesa hosts show cursor`

## Declared surfaces (repository evidence)

| Path | Meaning |
| --- | --- |
| `.cursor/mcp.json` | MCP server registrations |
| `.cursor/rules/**` | Project rules |
| `.cursorrules` | Legacy instructions |
| `AGENTS.md` | Agent instructions |
| `skills/**/SKILL.md` | Skills |

These establish **declared** configuration (`SOURCE_STATIC`).

## Effective permissions (NOT VERIFIED from files alone)

- Whether MCP servers are enabled for the workspace
- Tool allowlists / auto-run / approval mode
- OS user and environment inheritance of the Cursor process
- Whether skills/rules are actually loaded for a session

Mark host integration verified only with independent `HOST_CONFIGURATION` or authorized `RUNTIME` evidence.
