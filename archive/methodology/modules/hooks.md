# Module: Hooks and Lifecycle Handlers

**AESA module ID:** `HOOKS`  
**Procedure reference:** Section 10.6 of `prompts/02-modules.md` (core: `prompts/01-core-prompt.md`)
**Applies when:** component type is `Hook` / lifecycle handler, or host configuration registers pre/post tool, session, file, or error hooks.

Hooks can inherit excessive host privileges and may bypass interactive approval paths if not independently enforced.

## Inspection surfaces

- Hook type, event source, triggers/filters
- Lifecycle phase (pre/post tool, session start/end, file change, error/shutdown, etc.)
- Script/executable path and input/output format
- Environment, working directory, timeout, retry behavior
- Registration/removal, scope/inheritance, update path
- Execution identity and privilege context

## Checklist

- [ ] Exact hook identity, path, trigger conditions recorded
- [ ] Shell/process execution and child-process creation reviewed
- [ ] Filesystem / network / credential access reviewed
- [ ] Untrusted arguments from tool input/output assessed
- [ ] Environment inheritance reviewed
- [ ] Temporary files, path traversal, symlink handling reviewed
- [ ] Recursive triggering / hidden execution assessed
- [ ] Approval bypass and audit-suppression paths assessed
- [ ] Allowlists present and fail-open vs fail-closed behavior determined
- [ ] Revocation and disablement path reviewed
- [ ] Chaining with Skills / Automations / Subagents assessed (cross-component)

## High-priority attack paths

- Hook + shell + background Automation
- Pre-tool hook mutating arguments after user approval (TOCTOU)
- Post-tool hook exfiltrating sensitive tool results
- Session-start hook establishing persistence or elevated context

## Passive-audit constraints

- Do not execute hooks or register them in a live host during the passive audit.
- Mark runtime fail-open/fail-closed behavior `NOT VERIFIED` unless evidenced by configuration or authorized staging tests.
