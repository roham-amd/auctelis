# Reach definition (v1)

**Reach** is what a declared agent configuration can contact or launch — not
what it is proven to do at runtime.

```
reach = destination host set ∩ launcher identity ∩ capabilities ∩ pin
```

| Term | Meaning |
| --- | --- |
| Destination host set | URL hosts and declared destination hosts on a record |
| Launcher identity | Executable / transport (`npx`, `uvx`, `node`, URL transport, …) |
| Capabilities | Normalized capability labels (network, secrets, execute, tools, …) |
| Pin | Pin posture (`floating` / `pinned` / `digest` / …) |

## Change classes humans should see first

| Signal | Meaning |
| --- | --- |
| New destination | A host that was not in the sealed baseline (incl. `curl|sh` hosts) |
| New executable | A launcher / argv digest change on an identity |
| New secrets | New `env_keys` or secrets-class capabilities |
| Permission posture | Host settings `approval_posture` / `permission_allows` (e.g. bypass) |
| Inventory | Skills, commands, and other sealable records — **all sealed and available via `--top` / `--json` / the lock**; the terminal shows the top N by default |

## Tiers and trust

| Tier | Label | Meaning |
| --- | --- | --- |
| 0 | silent | Representation / instructions only |
| 1 | comment | Network reach (including inferred doc links) |
| 2 | fail | Execute, secrets, approvals, unattended, or new MCP/hook/host authority |

Plain CI workflows without agent steps or unattended triggers stay below tier 2
(tier 0 when no secrets are referenced, tier 1 when secrets are referenced) so
normal repository CI edits do not page CODEOWNERS. Agent CI workflows escalate
to tier 2 on agent-step evidence.

Tier 2 requires **literal** evidence: declared `env_keys` or a launcher on the
record. A record whose only evidence is `INFERRED_HINT` prose is capped at tier
1 even when the prose mentions secrets or execution — a doc link cannot page a
CODEOWNER the way a committed `env:` block does. The card says
`tier 1 (inferred hint)` rather than naming a capability the config never
declared.

`.auctelis/trusted-hosts` (written by `auctelis trust <host>`) lowers
**network-only** records whose destinations are all trusted to tier 1. It never
lowers execute, secrets, approvals, unattended, env-key reach, records that
declare a launcher, or **new MCP / Hook / Host Settings** authority (those
kinds stay at tier 2 even when every destination is allowlisted). Entries must
be specific hosts (TLD-only and wildcard entries are ignored).
`trust --init` writes a starter list; nothing is trusted implicitly.

The trust file is itself authority: a PR could allowlist its own destination.
The gate honors it only when CODEOWNERS covers `.auctelis/trusted-hosts` (or the
`.auctelis/` directory); otherwise trust is ignored for that run and the report
says so. `init` adds that CODEOWNERS entry.

Cards show the tier and its reason (`tier 2 (secrets)`), plus secret **names**
(`env: API_TOKEN`) — never values. `auctelis check --pins` lists unpinned
npx/uvx/docker MCP launchers with a concrete pin suggestion. Tightening an MCP
`pin_state` alone (`floating`/`unknown` → `pinned`/`digest`) is a **REDUCTION**
(PASS), and the card still shows `pin: unpinned → pinned`. Same-package argv
pinning (identical `package_stem` / launcher / host, e.g.
`@linear/mcp` → `@linear/mcp@1.2.3`) is also **REDUCTION**. Swapping the
package, launcher, or host — even when paired with a pin — is never
`REDUCTION` (AUCT-030).

## What reach is not

- Not publisher verification (`publisher NOT VERIFIED` until separately attested)
- Not effective sandbox / approval enforcement
- Not a runtime egress firewall

Schema: [`../schemas/authority-lock.schema.json`](../schemas/authority-lock.schema.json)  
Contract detail: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md)
