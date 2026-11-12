# Agent authority review playbook

One page for humans reviewing agent-config diffs. Graduate to
`authdiff lock` + CODEOWNERS when ready. Distilled from archived modules —
not a substitute for the scanner.

## Report questions (every Authority Diff)

| Question | Required answer |
| --- | --- |
| What changed? | Specific authority delta |
| Who is affected? | Agent, component, principal |
| What can it do? | Explicit capabilities |
| Where can it act? | Filesystem, destination, endpoint |
| How certain are we? | Declared / Configured / Effective / Verified |
| What evidence proves it? | Evidence ids + paths |
| What is unknown? | Coverage / unparsed gaps |
| What should happen next? | Approve, reject, investigate, remediate |

## Before you merge

Answer these on any PR that touches MCP, skills, hooks, subagents, host
settings, or agent CI steps:

1. **What new authority is introduced?** Command, URL, env, hook, skill tools.
2. **Who receives it?** Package publisher, remote host, hook script identity.
3. **Is the launcher pinned?** Exact version or digest — not `npx -y`, `@latest`, `:latest`.
4. **Can it run after approval without re-prompt?** Hooks / mutable MCP args (MCPoison-class).
5. **Does project scope auto-trust MCP or bypass permissions?**
6. **Any `*_BASE_URL` / proxy override that can steal tokens?**
7. **Secrets in env literals?** Prefer `${ENV}` placeholders; rotate if leaked.
8. **Cleartext `http://` remote MCP?** Require HTTPS.
9. **SKILL.md install prerequisites?** `curl|sh`, encoded commands, “install this first”.
10. **Invisible Unicode / bidi in instructions?**
11. **CI: `pull_request_target` + agent steps + write token?**
12. **Subagent tool inheritance broader than parent intent?**

If any answer is unknown, mark **NOT VERIFIED** — do not treat absence of a
scanner finding on `MANUAL_ONLY` surfaces as safety.

## PR template (snippet)

```markdown
## Agent authority
- [ ] AUTHORITY.lock updated (or N/A — no agent surfaces)
- [ ] Launchers pinned (version/digest)
- [ ] No project MCP auto-approve / permission bypass
- [ ] No new remote MCP / hooks without CODEOWNER ack
- [ ] Coverage gaps acknowledged (browser / memory / …)
```

## CODEOWNERS

Prefer CODEOWNERS coverage for `AUTHORITY.lock` plus a GitHub ruleset that
requires code-owner review (and dismisses stale approvals). `authdiff gate`
labels growth and checks that protection exists — it does not count PR reviews.

```text
AUTHORITY.lock  @security-owner
.authdiff.yml       @security-owner
**/.mcp.json    @security-owner
**/.cursor/mcp.json @security-owner
**/.claude/settings.json @security-owner
```

## Tooling path

```bash
# Git install only today — PyPI not published yet
uvx --from "git+https://github.com/roham-amd/authdiff.git@v0.3.2#subdirectory=tools" authdiff doctor
authdiff vet <url-or-path>
authdiff ci init --owner @you && authdiff lock --accept-gated
authdiff demo   # canned bad fixture + PR comment (exits 0)
# scan --base-lock is advisory; gate is the authority-growth verdict:
authdiff gate --base-lock AUTHORITY.lock
```
