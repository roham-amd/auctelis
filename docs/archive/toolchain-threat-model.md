# AESA toolchain threat model (initial)

Scope: **AESA deterministic tooling** (`tools/authdiff/`) introduced in 2.0.0. Prompt-only guardrails remain in `archive/methodology/prompts/04-passive-guardrails.md`.

## Assets

- Auditor machine filesystem and environment variables
- Target repository content (untrusted)
- Generated inventory and validation outputs

## Trust boundaries

| Boundary | Policy |
| --- | --- |
| Target → collector | Read-only; no execution; symlinks not followed |
| Target → parsers | Bounded size/depth; JSON/text only in pilot adapters |
| Collector → network | **No network** in passive inventory mode |
| Tooling → LLM | Out of scope for tooling; prompts remain separate |

## Threats (selected)

1. **Path traversal / symlink escape** — mitigated by not following symlinks; record events.
2. **Archive bombs / huge files** — partial: file size and count limits in collector; archive adapters not shipped yet.
3. **Parser differential** — JSON/YAML parsers must fail closed with visible errors.
4. **Instruction injection in target Markdown** — tooling must not interpret Skill/MCP file content as operator instructions.
5. **Supply chain of AESA tools** — install with `uv sync --locked` (exact versions + hashes in `tools/uv.lock`); Dependabot weekly `uv` + `github-actions` updates (`.github/dependabot.yml`) with review before merge; review adapter changes.

## Residual risks

- Incomplete adapter coverage may imply false confidence — maturity flags required.
- Semantic validation does not prove factual truth of claims.
- Future R-008 external tool invocation needs separate threat model section.

## Validation

Malicious parser fixtures are tracked under corpus family *Parser/audit-tool abuse*. Tooling cases currently include CORPUS-001–010; agent-detection stubs live under `tests/benchmark/` (BENCH-001+).

See assessment R-013 for full hardening requirements.
