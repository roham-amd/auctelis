# Claude Code host profile

**Support:** PARTIAL  
**CLI:** `aesa hosts show claude-code`

## Declared surfaces (repository evidence)

| Path | Meaning |
| --- | --- |
| `CLAUDE.md` | Project memory / instructions |
| `.claude/**` | Local Claude Code settings |
| `.mcp.json` | MCP registrations |
| `skills/**/SKILL.md` | Skills |
| `hooks/**` | Lifecycle hooks |

## Effective permissions (NOT VERIFIED from files alone)

- Permission mode actually enforced by Claude Code
- Hook execution identity and credential inheritance
- Whether `CLAUDE.md` / skills auto-load for the session
- Network and filesystem sandbox behavior

Do not promote declared settings to effective permissions without host or runtime evidence.
