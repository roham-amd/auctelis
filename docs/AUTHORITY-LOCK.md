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

## Approval records

Human decisions bind to the sealed authority hash via `approvals[]`:

| Field | Purpose |
| --- | --- |
| `owner` | Accountable reviewer identity |
| `approved_at` | UTC timestamp |
| `lock_hash` | Exact sealed authority hash being accepted |
| `audited_commit` | Repository commit under review |
| `policy_hash` | Policy version at approval time |
| `justification` | Why the authority state is accepted |
| `exceptions` | Optional accepted findings with expiry |

```bash
authdiff lock --approval @security-owners
```

Approvals are append-only metadata; they are **not** part of the sealed
`lock_hash` of the authority records. Agents must not write approvals
(`AUTHDIFF_AGENT=1` refuses mutating `lock`).

`approved_findings[]` is the rejected/accepted risk register for individual
finding fingerprints (owner + justification + optional expiry).

---

## Commands

```bash
authdiff lock                 # write / update AUTHORITY.lock
authdiff lock --approval @me  # also append a human approval record
authdiff lock --check         # exit 1 on drift
authdiff check --locked .     # scan + lock drift gate
authdiff diff lock A.lock B.lock
```

Protect the file:

```text
# CODEOWNERS
AUTHORITY.lock  @org/security-owners
```

`authdiff ci init` writes a CODEOWNERS stub for this path.

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
