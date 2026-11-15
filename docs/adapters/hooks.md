# Hooks (`hooks` + `claude_settings` + Cursor hooks)

| | |
| --- | --- |
| Maturity | PARTIAL |
| Establishes | CONFIGURED hook files, lifecycle event names, execution/bypass/download hints, host-identity inheritance signal |
| Does not establish | That the host registers the hook; EFFECTIVE env inheritance; approval bypass at runtime |
| Formats | `hooks.json`, `hooks/`, Claude `.claude/settings*.json` hooks blocks, Cursor `~/.cursor/hooks.json` |
| Fixtures | Claude settings RULE-017/018/019 fixtures; `eval/configs/cfg-005-hooks-sessionstart` |
| Unknown / report | Host-global hooks outside the repository |

## Product note

auctelis **inventories** hook configs as authority-bearing surfaces (reach in
`AUTHORITY.lock`, growth on the PR Authority Diff). It does **not** install or
arm host tripwires. Public `watch` / `allow` / `hook` CLIs were removed.

Review hook files the same way as MCP and skills: seal with `lock --update`,
require CODEOWNERS on growth, use `auctelis why <name>` for the exact path.
