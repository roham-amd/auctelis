# Hooks (`hooks` + `claude_settings` + Cursor hooks)

| | |
| --- | --- |
| Maturity | PARTIAL |
| Establishes | CONFIGURED hook files, lifecycle event names, execution/bypass/download hints, host-identity inheritance signal |
| Does not establish | That the host registers the hook; EFFECTIVE env inheritance; approval bypass at runtime |
| Formats | `hooks.json`, `hooks/`, Claude `.claude/settings*.json` hooks blocks, Cursor `~/.cursor/hooks.json` |
| Fixtures | Claude settings RULE-017/018/019 fixtures; `eval/configs/cfg-005-hooks-sessionstart` |
| Unknown / report | Host-global hooks outside the repository |

## Cursor hook contract

`auctelis watch --arm` / `auctelis hook install` writes
`~/.cursor/hooks.json` with these events:

| Event | auctelis script | Behaviour |
| --- | --- | --- |
| `sessionStart` | `auctelis-session-delta.py` | Prints the one-screen delta; quiet when nothing changed |
| `beforeMCPExecution` | `auctelis_cursor_hook.py` | Denies a server absent from `AUTHORITY.lock`; empty allowlist is deny-all |
| `beforeShellExecution` | `auctelis_cursor_hook.py` | Denies shell commands that touch authority-bearing paths |
| `beforeFileEdit` | `auctelis_cursor_hook.py` | Denies edits to authority-bearing paths |

Cursor passes JSON on stdin and expects a JSON decision on stdout:
`{"permission": "allow" | "deny", "user_message": "..."}`. Unknown events fail
open. This is a **tripwire**, not a sandbox: it does not verify publisher
identity, effective host permissions, or runtime behaviour.

`auctelis hook status` reports, for Cursor and Claude Code:

| State | Meaning |
| --- | --- |
| `not_wired` | No auctelis entries in host settings |
| `not_firing` | Wired but script missing or CLI not on PATH |
| `not_armed` | Wired, but no `~/.auctelis/AUTHORITY.lock` yet |
| `wired, not yet observed` | Armed; no heartbeat from a session yet |
| `firing (last: …)` | Session hook wrote a heartbeat |
