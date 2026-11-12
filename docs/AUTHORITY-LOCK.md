# AUTHORITY.lock contract

`AUTHORITY.lock` is the product’s central artifact: the **approved authority
state** for a repository. It is more important than a long audit report.

Schema: [`../schemas/authority-lock.schema.json`](../schemas/authority-lock.schema.json)  
Implementation: `tools/authdiff/authority_lock.py`  
Version field: `version: 1` (record-level identity; sealed hash excludes volatile path/commit metadata)

---

## What the lock represents

| It records | It does not record |
| --- | --- |
| Observed authority-bearing components at lock time | Proof of effective runtime permissions |
| Capabilities, destinations, env keys, pin/approval posture | That a component is “safe” |
| Content digests / fingerprints for drift detection | Publisher trust or SBOM attestation (unless separately evidenced) |
| Policy file hash when `.authdiff.yml` is present | Automatic approval of future expansions |

Updating the lock **is** the approval workflow: commit + CODEOWNERS review.

---

## Identity model

| Field | Meaning |
| --- | --- |
| `identity_key` | Stable join key: `host\|kind\|name` (case-folded). **Path-independent.** |
| `id` | Display id: `host/kind/name@path`. Changes when a file moves. |
| `fingerprint` | Content-derived component fingerprint |
| `digest` | Source file content digest when available |

**Equivalence:** two records with the same `identity_key` are the same authority
component for diff purposes, even if `path` / `id` / `digest` differ.

**Collision:** if two components share host/kind/name, matching falls back to
full `id` (path-qualified).

---

## What counts as an authority change

| Class | Meaning | Typical trigger |
| --- | --- | --- |
| `addition` | New authority identity | Component with a new `identity_key` |
| `expansion` | Broader authority on an existing identity | New capabilities / destinations / env keys; weaker pin; looser approval |
| `reduction` | Narrower authority | Removed component; fewer caps/destinations/env; stronger pin; stricter approval |
| `replacement` | Authority shape rewritten without clear grow/shrink | Equal-size capability set rewrite |
| `representation` | Packaging / location / digest only | Path move, content reformat with same authority fields |
| `mixed` | Both expansion and reduction on one record | Caps added and removed in one edit |

Pin ranking (worse →): `digest` &lt; `pinned` &lt; `n/a` &lt; `unknown` &lt; `floating`  
Approval ranking (worse →): `prompt` &lt; `unknown` &lt; `auto` &lt; `bypass`

Diff summary fields:

- `meaningful_authority_change` — additions / expansions / reductions / replacements / policy
- `authority_changed` — any lock drift including representation (requires re-lock)

`authdiff lock --check` and `check --locked` fail when `authority_changed` is
true so digests stay honest. Reviewers should prioritize `meaningful_authority_change`.

---

## Human review (GitHub-native)

`approvals[]` on the lock is **legacy / empty** — authdiff does not treat
self-asserted lock approvals as a gate input. Review is enforced by:

1. CODEOWNERS coverage for `AUTHORITY.lock` (and other authority paths)
2. A GitHub ruleset (or branch protection) requiring code-owner review
3. `authdiff gate` labeling GROWTH vs REDUCTION vs the base-ref lock

`approved_findings[]` remains the explicit `--accept-gated` register for
HIGH/CRITICAL findings sealed into a baseline (optional `acceptance_note`
when `--approval` is also passed). Agents must not mutate locks
(`AUTHDIFF_AGENT=1`).

---

## Commands

```bash
authdiff lock                              # write / update AUTHORITY.lock
authdiff lock --accept-gated [--approval @me]  # seal gated findings (notes only)
authdiff lock --check                      # exit 1 on drift
authdiff check --locked .                  # scan + lock drift gate
authdiff gate --base-lock base.lock        # growth label + CODEOWNERS/ruleset
authdiff diff lock A.lock B.lock
```

Protect the file:

```text
# CODEOWNERS — prefer @user; GitHub rulesets enforce @org/team membership.
AUTHORITY.lock  @security-owner
```

`authdiff ci init --owner @you` writes a CODEOWNERS stub for this path.

### Pinned facts (0.3.0)

Each record may also seal:

| Field | Meaning |
| --- | --- |
| `launcher` | Executable / transport (`npx`, `uvx`, `node`, …) |
| `args_digest` | SHA-256 of canonical JSON argv |
| `url_host` | Hostname for URL MCP transports |
| `script_digest` | Content digest for hooks / skill trees |

Same identity with a different launcher/args/host is a **`replacement`** (needs approval).
Opt-in: `authdiff lock --snapshot tools.json` merges `mcp_tools` description pins;
`authdiff lock --home` seals `~/.authdiff/AUTHORITY.lock`.

---

## Unknown / unparseable components

- Components the adapters cannot parse are **not** silently approved by a lock.
- Unparsed agent configs fail closed in scan decisions (`REVIEW`).
- Families with `MANUAL_ONLY` / `UNSUPPORTED` maturity appear in coverage, not
  as lock records of “safe absence”.

See [`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md).

---

## Migration

- **v1 → v2:** regenerate with `authdiff lock` (record-level format).
- Adding `identity_key` is backward compatible: older locks without the field
  are keyed via computed `host|kind|name` at diff time.
- Do not hand-edit `lock_hash`; it is recomputed on write.

---

## Anti-patterns

- Rubber-stamping lock updates without reading expansion lines
- Treating representation churn as a security regression
- Using suppressions in `.authdiff.yml` instead of reviewing lock expansions
- Letting a PR edit policy on the head ref without `trusted-policy` from base
