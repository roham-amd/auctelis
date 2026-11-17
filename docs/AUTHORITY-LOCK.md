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
| `representation` | Packaging / location / body digest only | Path move; instruction/skill `script_digest` wording change with same reach fields |
| `mixed` | Both expansion and reduction on one record | Caps added and removed in one edit |

Pin ranking (worse →): `digest` &lt; `pinned` &lt; `n/a` &lt; `unknown` &lt; `floating`  
Approval ranking (worse →): `prompt` &lt; `unknown` &lt; `auto` &lt; `bypass`

Diff summary fields:

- `max_reach_tier` — 0 silent / 1 comment / 2 fail (see [`REACH.md`](REACH.md) + `reach_tiers.py`)
- `material_authority_change` — `max_reach_tier >= 2` (execute / secrets / new MCP / env / floating launchers / agent CI). Required CI fails on this **when locked**
- `meaningful_authority_change` — any non-representation delta (additions / expansions / reductions / …)
- `authority_changed` — any lock drift including representation (requires re-lock)

Rendered lock / PR lines include **field-level old → new** for capabilities,
destinations, env keys, pin/approval posture, launcher, and digests, plus the
evidence path (`@ path`). Body-only edits surface `body changed`; path moves
surface `path: old → new`. Prose that adds a destination host is an
**expansion** at comment tier (`INFERRED_HINT`) unless execute/secrets evidence
is also present — visible on the PR comment, not a required-check fail alone.

`auctelis lock --check` and local `check` fail when `authority_changed` is
true so digests stay honest. The required CI gate fails on
`material_authority_change` / lock↔tree drift / unparsed / CODEOWNERS gaps
**when `locked=true`**, not on body-only representation or comment-tier
doc-link growth.

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
auctelis check                             # repo authority vs AUTHORITY.lock
auctelis lock --update                     # write / refresh repo AUTHORITY.lock
auctelis lock --check                      # exit 1 on drift
auctelis init --owner you                 # comment-only workflow + CODEOWNERS + lock
auctelis init --owner you --enforce       # opt into locked + strict ruleset
auctelis gate --base-lock base.lock        # PR Authority Diff + CODEOWNERS gate
auctelis why <name>                        # exact config path for one record
```

Pass a lock **file** to `--base-lock` (for example `base.lock` or the path
extracted from the base ref). A directory such as `.` fails closed.

Protect the file:

```text
# CODEOWNERS — prefer @user; GitHub rulesets enforce @org/team membership.
AUTHORITY.lock  @security-owner
```

`auctelis init --owner you` merges a CODEOWNERS stub for this path.

### Pinned facts

Each record may also seal:

| Field | Meaning |
| --- | --- |
| `launcher` | Executable / transport (`npx`, `uvx`, `node`, …) |
| `args_digest` | SHA-256 of canonical JSON argv |
| `url_host` | Hostname for URL MCP transports |
| `script_digest` | Content digest for hooks / skill trees |
| `evidence_strength` | `LITERAL_CONFIG` / `INFERRED_HINT` / `NAME_MARKER` |

Same identity with a different launcher/args/host is a **`replacement`** (needs approval).
Opt-in: `auctelis lock --snapshot tools.json` merges `mcp_tools` description pins.

Host tripwires (`watch` / `allow` / `hook`) and public scanner CLIs are
**removed**. Product path: diff --base → init --owner team → check → gate.

---

## Unknown / unparseable components

- Components the adapters cannot parse are **not** silently approved by a lock.
- Unparsed agent configs surface as coverage gaps / `REVIEW` in maintainer
  annotations (`auctelis-dev`); they do not silently pass the product gate.
- Families with `MANUAL_ONLY` / `UNSUPPORTED` maturity appear in coverage, not
  as lock records of “safe absence”.
- An empty baseline is normal: first growth is CODEOWNERS review of the lock,
  not forever `FAIL_CLOSED`.

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
