# Auctelis Claude Code plugin (archived optional bundle)

Compatibility stub for Claude Code. **Not** the product install path.

Prefer:

```bash
auctelis check
auctelis lock --update
auctelis ci init --owner @security
```

## Optional tripwires (archived)

```bash
auctelis watch --arm
# or
auctelis hook install
```

This wires absolute-path hooks into `~/.claude/settings.json`. Scripts live under
`tools/auctelis/templates/`. Tripwires are not a sandbox.

| Command | Purpose |
| --- | --- |
| `/auctelis` (skill) | Explain current delta; never seal |
| `auctelis why <name>` | Exact config path |
| `auctelis hook status --probe` | Script deny probe (not host-wiring proof) |
