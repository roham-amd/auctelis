# Agent authority review playbook

One page for humans reviewing agent-config diffs. The weekly habit is the
`auctelis watch` delta in Cursor or Claude; graduate to a repo
`AUTHORITY.lock` + CODEOWNERS when a team needs the merge gate. This is the
fallback if hook retention is zero at week 4 — not a substitute for the delta.

## Report questions (every Authority Diff)

| Question | Required answer |
| --- | --- |
| What changed? | Specific authority delta |
| Who is affected? | Agent, component, principal |
| What new reach does this add? | Explicit capabilities |
| Where can it act? | Filesystem, destination host, endpoint |
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
requires code-owner review (and dismisses stale approvals). `auctelis gate`
labels growth and checks that protection exists — it does not count PR reviews.

```text
AUTHORITY.lock  @security-owner
.auctelis.yml       @security-owner
**/.mcp.json    @security-owner
**/.cursor/mcp.json @security-owner
**/.claude/settings.json @security-owner
```

## Tooling path

```bash
# Git install only today — PyPI not published yet
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.5.0#subdirectory=tools"

auctelis watch              # one-screen declared authority delta
auctelis watch --seal       # human baseline (no approval fields are written)
auctelis watch --arm        # Cursor + Claude session/tool hooks
auctelis ci init --owner @you   # lockless workflow + CODEOWNERS
auctelis demo               # canned fixture + PR comment (exits 0)
# scan --base-lock is advisory; gate is the authority-growth verdict:
auctelis gate --base-lock AUTHORITY.lock
```

If the tree already has high/critical annotations, fix them first. Sealing with
`--accept-gated` is an explicit human override; it records **no** approval —
CODEOWNERS and rulesets are the approval system.

