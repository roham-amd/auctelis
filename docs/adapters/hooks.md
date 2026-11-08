# Hooks (`hooks` + `claude_settings`)

| | |
| --- | --- |
| Maturity | PARTIAL |
| Establishes | CONFIGURED hook files, lifecycle event names, execution/bypass/download hints, host-identity inheritance signal |
| Does not establish | That the host registers the hook; EFFECTIVE env inheritance; approval bypass at runtime |
| Formats | `hooks.json`, `hooks/`, Claude `.claude/settings*.json` hooks blocks |
| Fixtures | Claude settings RULE-017/018/019 fixtures |
| Unknown → report | Host-global hooks outside the repository |
