# Auctelis Cursor bundle (archived optional)

Compatibility stub for Cursor. **Not** the product install path.

Prefer:

```bash
auctelis check
auctelis lock --update
auctelis ci init --owner @security
```

## Optional tripwires (archived)

```bash
auctelis watch --arm
# wires ~/.cursor/hooks.json with absolute interpreter paths
```

Optional: copy `skills/cursor/AUCTELIS.md` into project `.cursor/rules/` or use
`skills/auctelis-auditor/`. Tripwires are not a sandbox.
