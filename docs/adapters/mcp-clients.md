# MCP clients (`mcp_config`)

| | |
| --- | --- |
| Maturity | PARTIAL |
| Establishes | CONFIGURED launcher identity, args, env **keys**, transport URL, pin/unpinned signals |
| Does not establish | Remote server tool authz, EFFECTIVE host binding, VERIFIED runtime tools |
| Formats | `.cursor/mcp.json`, `.vscode/mcp.json`, `.mcp.json`, Claude MCP maps, examples |
| Fixtures | `tests/rules/fixtures/rule-011-*`, `rule-012-*`, `rule-013-*`, `rule-021-*` |
| Known FP risk | Template/example configs (RULE-009); placeholders in env values |
| Unknown → report | Unparsed JSONC, oversize files, host-only registrations outside the repo |
