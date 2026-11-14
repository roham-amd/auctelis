# AUTHORITY.lock contract

`AUTHORITY.lock` is the product’s central artifact: the **approved authority
state** for a repository. It is more important than a long audit report.

Schema: [`../schemas/authority-lock.schema.json`](../schemas/authority-lock.schema.json)  
Reach definition: [`REACH.md`](REACH.md)  
Implementation: `tools/auctelis/authority_lock.py`  
Version field: `version: 1` (frozen public lockfile standard; sealed hash excludes volatile path/commit metadata)

---

## What the lock represents

| It records | It does not record |
| --- | --- |
| Observed authority-bearing components at lock time | Proof of effective runtime permissions |
| Capabilities, destinations, env keys, pin/approval posture | That a component is “safe” |
| Content digests / fingerprints for drift detection | Publisher trust or SBOM attestation (unless separately evidenced) |
| Policy file hash when `.auctelis.yml` is present | Automatic approval of future expansions |

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

Rendered lock / PR lines include **field-level old → new** for capabilities,
destinations, env keys, pin/approval posture, launcher, and digests, plus the
evidence path (`@ path`). Representation-only moves surface `path: old → new`.

`auctelis lock --check` and `check --locked` fail when `authority_changed` is
true so digests stay honest. Reviewers should prioritize `meaningful_authority_change`.

---

## Human review (GitHub-native)

`approvals[]` on the lock is **legacy / empty** — auctelis does not treat
self-asserted lock approvals as a gate input. Review is enforced by:

1. CODEOWNERS coverage for `AUTHORITY.lock` (and other authority paths)
2. A GitHub ruleset (or branch protection) requiring code-owner review
3. `auctelis gate` labeling GROWTH vs REDUCTION vs the base-ref lock

`approvals[]` and `approved_findings[]` are emitted **empty** for schema
compatibility and are never gate inputs. `--accept-gated` is only an explicit
human override to seal the current (imperfect) state; it records no approval.
Agents must not mutate locks (`AUCTELIS_AGENT=1`).

---

## Commands

```bash
auctelis watch                             # highlights (first run) or sealed delta
auctelis watch --seal                      # seal ~/.auctelis/AUTHORITY.lock
auctelis watch --arm                       # Cursor + Claude session/tripwire hooks
auctelis watch --delta-only                # changed lines only (session hook)
auctelis why <name>                        # exact config path for one record
auctelis hook status                       # wired / not yet observed / firing
auctelis lock                              # write / update repo AUTHORITY.lock
auctelis lock --check                      # exit 1 on drift
auctelis gate --base-lock base.lock        # optional team upsell (hidden help)
auctelis diff lock A.lock B.lock           # hidden
```

Protect the file:

```text
# CODEOWNERS — prefer @user; GitHub rulesets enforce @org/team membership.
AUTHORITY.lock  @security-owner
```

`auctelis ci init --owner @you` writes a CODEOWNERS stub for this path.

### Pinned facts (0.3.0)

Each record may also seal:

| Field | Meaning |
| --- | --- |
| `launcher` | Executable / transport (`npx`, `uvx`, `node`, …) |
| `args_digest` | SHA-256 of canonical JSON argv |
| `url_host` | Hostname for URL MCP transports |
| `script_digest` | Content digest for hooks / skill trees |

Same identity with a different launcher/args/host is a **`replacement`** (needs approval).
Opt-in: `auctelis lock --snapshot tools.json` merges `mcp_tools` description pins;
`auctelis lock --home` seals `~/.auctelis/AUTHORITY.lock`.

---

## Unknown / unparseable components

- Components the adapters cannot parse are **not** silently approved by a lock.
- Unparsed agent configs fail closed in scan decisions (`REVIEW`).
- Families with `MANUAL_ONLY` / `UNSUPPORTED` maturity appear in coverage, not
  as lock records of “safe absence”.

See [`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md).

---

## Migration

- The on-disk lock format is **v1**; there is no v2 reader/writer in this release.
- Adding `identity_key` is backward compatible: older locks without the field
  are keyed via computed `host|kind|name` at diff time.
- Do not hand-edit `lock_hash`; it is recomputed on write.

---

## Anti-patterns

- Rubber-stamping lock updates without reading expansion lines
- Treating representation churn as a security regression
- Using suppressions in `.auctelis.yml` instead of reviewing lock expansions
- Letting a PR edit policy on the head ref without `trusted-policy` from base
