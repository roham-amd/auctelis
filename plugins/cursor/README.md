# Auctelis Cursor bundle

Hooks + skill for Cursor: SessionStart delta, beforeMCPExecution tripwire, and
the auditor skill that explains deltas without sealing.

## Install

```bash
auctelis watch --arm
# wires ~/.cursor/hooks.json with absolute interpreter paths
```

Optional: copy `skills/cursor/AUCTELIS.md` into your project `.cursor/rules/` or
enable the packaged skill under `skills/auctelis-auditor/`.

## First-user path

1. Clone a repo and open it in Cursor.
2. `auctelis watch` — every sealable record is on screen.
3. `auctelis watch --seal --accept <digest>`
4. `auctelis allow` for project-level MCP / settings.
5. Session greeting speaks only on change; MCP not in the lock is denied.
