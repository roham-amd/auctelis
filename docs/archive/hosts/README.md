# Agent host assessment profiles

authdiff distinguishes **declared** host configuration (files in the repository) from **effective** host permissions (what the running agent can actually do).

| Host id | Support | Notes |
| --- | --- | --- |
| `cursor` | PARTIAL | `.cursor/`, MCP registrations, rules, skills |
| `claude-code` | PARTIAL | `CLAUDE.md`, `.claude/`, `.mcp.json`, hooks |
| `github-copilot` | MANUAL_ONLY | Instruction files only; effective rights rarely in-repo |

## Commands

```bash
aesa hosts list
aesa hosts show cursor
aesa hosts show claude-code
```

Inventory adapter `host_profiles` emits `Agent Host` components with:

- `permission_scope: DECLARED_ONLY`
- `effective_permissions: NOT VERIFIED`

## What profiles are not

- Not proof the host is used in production
- Not effective IAM / approval enforcement
- Not a substitute for runtime validation

See [`cursor.md`](cursor.md) and [`claude-code.md`](claude-code.md).
