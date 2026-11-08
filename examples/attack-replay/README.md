# Attack-replay corpus ("Metasploitable for agent config")

Runnable, **inert** malicious-repo fixtures. Payloads only touch a local canary
listener (or encode clearly fake hosts). Hosts, scanners, and policies can
regress against these without contacting the public internet.

## Fixtures

| ID | Surface | Expected authdiff signal |
| --- | --- | --- |
| `01-sessionstart-curl-env` | Claude settings hook | RULE-015 / RULE-004 |
| `02-enable-all-project-mcp` | Claude settings | RULE-018 / RULE-017 |
| `03-base-url-hijack` | Claude env override | RULE-019 |
| `04-mcp-bash-pipe` | MCP `bash -c` | RULE-015 |
| `05-skill-sudo-pipe` | SKILL.md | RULE-015 |
| `06-hidden-html-comment` | SKILL.md HTML comment | RULE-010 |
| `07-jsonc-padded-mcp` | oversize / JSONC evasion | REVIEW (unparsed) or parse+find |
| `08-pr-target-agent` | GitHub workflow | RULE-016 |
| `09-literal-mcp-secret` | MCP env literal | RULE-012 |
| `10-unpinned-npx` | MCP launcher | RULE-011 |

Canary convention: commands may mention `http://127.0.0.1:9/canary` (discard port)
so they are obviously inert.

Run:

```bash
authdiff scan examples/attack-replay/01-sessionstart-curl-env
authdiff atlas crawl --demo-seed
```
