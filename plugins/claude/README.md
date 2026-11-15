# Auctelis Claude Code plugin

Project Trust tripwire for Claude Code: SessionStart delta + PreToolUse allowlist.

## Install

```bash
# From a clone of auctelis (or after `uv tool install`):
auctelis watch --arm
# or
auctelis hook install
```

This wires absolute-path hooks into `~/.claude/settings.json`. No separate marketplace
package is required; the scripts under `tools/auctelis/templates/` are the plugin body.

## First-user path

1. Open a repo.
2. `auctelis watch` — review every record on screen (note the Accept digest).
3. `auctelis watch --seal --accept <digest>`
4. For project authority: `auctelis allow`
5. New session prints only deltas; unknown MCP is refused at PreToolUse.

## Commands

| Command | Purpose |
| --- | --- |
| `/auctelis` (skill) | Explain current delta; never seal |
| `auctelis why <name>` | Exact config path |
| `auctelis hook status --probe` | Prove tripwires deny |
