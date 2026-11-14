# Evidence, capabilities, findings, and claims

auctelis’s intellectual core is an **evidence-first** model. This document is normative for how deterministic tooling and AI auditors must treat facts.

Related: [`PRODUCT.md`](PRODUCT.md), [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md), [`SECURITY-RULES.md`](SECURITY-RULES.md).

---

## Five core objects

| Object | Meaning | Primary producer |
| --- | --- | --- |
| **Component** | What exists in the ecosystem | Inventory adapters |
| **Capability** | What it appears able to do | Capability extractor + modules |
| **Evidence** | What establishes a fact | Collectors, rules, humans, runtime (if authorized) |
| **Finding** | Security concern tied to evidence | Rules + AI/human review |
| **Relationship** | How components/capabilities connect | Emitted as POTENTIAL co-host composites (`relationships[]`); verified reachability is future work |

The audit **report** is a serialization of these objects — not the source of truth.

---

## Four authority layers (never conflate)

Product contract language (also emitted on every scan as `authority_layers`):

| Layer | What is established | Typical producer |
| --- | --- | --- |
| **Declared** | What the integration says it requires | Publisher manifest / config claims |
| **Configured** | What host/repo configuration appears to expose | Inventory adapters + rules |
| **Effective** | What the execution environment actually permits | Host profiles + authorized checks |
| **Verified** | What an authorized test independently established | Explicit opt-in runtime only |

Implementation detail: source adapters may also speak of *implemented* capability
(code appears able to X). That still maps to **Configured** until host/runtime
evidence promotes it to **Effective** / **Verified**.

Discovering `execute_commands` in an MCP integration does **not** establish that
the server can execute arbitrary commands under the developer's full identity.
Build findings around explicit trust-boundary relationships (principal, execution
identity, reachable secrets, destinations, tool authorization, human approval,
delegation) — not configuration patterns alone.

Assessment sequence for every component:

1. Who controls its source and updates?
2. Who or what loads it?
3. Under which identity does it run?
4. What can it read, write, execute, or communicate with?
5. What data can reach it / leave through it?
6. Can it delegate authority?
7. What prevents, limits, or observes that authority?
8. What evidence supports each conclusion?
9. What could not be established?

Model: **Actor → Component → Principal → Capability → Target → Boundary → Control → Impact**

---

## Capability vs exposure vs finding

Do **not** treat detection of a security-relevant capability as a vulnerability.

| Concept | Question | Example |
| --- | --- | --- |
| **Capability** | What can it potentially do? | MCP server launches a local command |
| **Exposure** | How reachable is that capability, and under which identity? | Remote endpoint; broad filesystem args |
| **Security finding** | Is there an evidenced violation of a security property? | Local MCP inherits unrestricted production credentials |

Capability origins (auctelis / findings contract 1.2+):

| Origin | Meaning |
| --- | --- |
| `DECLARED` | Explicitly present in configuration / instructions |
| `POTENTIAL` | Hint-derived; not independently verified |
| `TYPE_DEFAULT` | Assumed from component type alone — never “effective” |
| `EFFECTIVE` | Host/integration evidence of actual authority |
| `VERIFIED` | Independently verified (authorized runtime test) |

Finding classes emitted by rules: `CAPABILITY`, `EXPOSURE`, `SECURITY_FINDING`.

Evidence strength (findings contract **1.2**):

| Strength | Meaning | Typical rules |
| --- | --- | --- |
| `LITERAL_CONFIG` | Value taken from config/instruction bytes | Unpinned launcher, HTTP URL, literal env secret |
| `INFERRED_HINT` | Adapter hint / multi-signal inference | Most RULE-001…009 paths |
| `NAME_MARKER` | Path/name only — weak triage signal | RULE-010 |

Findings may also include `verify_in_60s` (reproduction hint) and `fix_snippet`.

---

## Evidence record fields

| Field | Purpose |
| --- | --- |
| `evidence_id` | Stable reference from report → source |
| `source_commit` | Exact assessed revision |
| `file_path` / `line_start` / `line_end` | Human-verifiable location |
| `content_digest` | Integrity of the inspected artifact |
| `parser_version` | Adapter / parser identity |
| `rule_pack_version` | Reproducibility of the finding |
| `authority_layer` | Declared / Configured / Effective / Verified |
| `derived_from` | Lineage of an inference |
| `limitations` | What the evidence cannot establish |

## Evidence classes

Never upgrade one class into another without new evidence.

| Class | Establishes | Does not establish |
| --- | --- | --- |
| `SOURCE_STATIC` | What is written in repository files | Runtime behavior, effective host policy |
| `ARTIFACT` | Bytes of a built/packaged artifact | That source equals the installed binary |
| `PROVENANCE` | Origin / signature / publisher claims (when evidenced) | Safety of behavior |
| `HOST_CONFIGURATION` | Declared host settings | That settings are enforced at runtime |
| `RUNTIME` | Observed execution in an authorized test | Behavior in other environments |
| `EXTERNAL_INTELLIGENCE` | Third-party advisories / intel | Applicability without local evidence |
| `USER_ASSERTION` | Operator-stated facts | Independent verification |

---

## Verification / claim status

| Status | Meaning |
| --- | --- |
| `OBSERVED` | Directly seen in evidence (e.g. config line present) |
| `CONFIRMED` | Independently verified; **requires evidence_ids** |
| `POTENTIAL` | Plausible path; missing links remain |
| `NOT VERIFIED` | Applicable but unevidenced |
| `NOT ASSESSED` | Out of scope for this engagement |
| `NOT APPLICABLE` | Not relevant (with reason) |

Guard rules emit `OBSERVED` or `POTENTIAL` only. AI auditors must not promote to `CONFIRMED` without cited evidence; a finding without `evidence_ids` is not a gate finding.

---

## Capability kinds

Extracted by `tools/auctelis/security/capabilities.py` and refined during deep review:

| Kind | Question |
| --- | --- |
| `read_files` | Can it read files? |
| `write_files` | Can it write files? |
| `execute_commands` | Can it execute commands? |
| `access_secrets` | Can it access secrets? |
| `access_network` | Can it reach the network? |
| `modify_agent_instructions` | Can it change agent instructions? |
| `invoke_tools` | Can it invoke other tools? |
| `delegate_tasks` | Can it delegate? |
| `modify_approvals` | Can it alter approval decisions? |
| `access_persistent_memory` | Can it access persistent memory? |
| `unattended_operation` | Can it run without a human present? |

Capability-first assessment is preferred over merely counting component types.

---

## Evidence record fields (chain of custody)

| Field | Purpose |
| --- | --- |
| `evidence_id` | Stable reference (`E-001`, `E-INV-C-001`, …) |
| `component_id` | Related component identity |
| `component_version` / source identity | Exact component version or source identity when known |
| `source_commit` | Exact audited revision when known |
| `artifact_digest` | Artifact digest when scanning a built package |
| `file_path` | Exact source location |
| `line_start` / `line_end` | Reproducible location when available |
| `content_digest` | Integrity of the observed bytes |
| `parser` / `adapter_version` | Which parser produced the observation |
| `rule_version` | Rule pack / rule id version when rule-derived |
| `evidence_class` | Class enum above |
| `collection_method` | `deterministic_rule`, `inventory_adapter`, human, … |
| `observed_at` | Collection timestamp |
| `verification_status` | Status enum |
| `derivation` | `directly_observed` \| `inferred` \| `user_supplied` |
| `limitations` | What this evidence cannot establish |
| `summary` | Short description |

Producers must populate `content_digest` and `source_commit` whenever the source
file and git commit are available, and `line_start`/`line_end` when a
configuration needle can be located. Findings reference evidence objects; AI
claims must not invent evidence by restating observations.

### Reproducibility question

A reviewer should be able to answer:

> Can I reproduce the same observation from the same component version, using
> the same parser and rule set?

`AUTHORITY.lock` must retain enough identity to distinguish a changed component
from a representation-only change ([`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md)).

### Approval record (GitHub-native)

Auctelis does **not** write a self-asserted approval chain into the lock. The
approval record is the Git history plus CODEOWNERS/rulesets:

| Surface | Purpose |
| --- | --- |
| `AUTHORITY.lock` commit | Exact sealed authority state |
| CODEOWNERS on `AUTHORITY.lock` | Required human reviewer |
| Ruleset requiring code-owner review | Enforcement of that reviewer |
| PR discussion / commit message | Why the state was accepted |

`approvals[]` and `approved_findings[]` are emitted empty for compatibility and
are never gate inputs. `auctelis gate` labels growth and checks protection; it
does not count PR approvals.

### Freshness vs strength

- **Freshness:** Is evidence still applicable to the current component version?
- **Strength:** How strongly does it support the claim?

A hash proves digest match — not safety. Model agreement is not independent verification.

### False-confidence controls

- Keep **severity** and **confidence** separate.
- Do not gate critical CI fails on `NAME_MARKER` alone.
- Abstain: unparseable / oversized / unsupported → explicit gap, never silent clean.
- Suppressions remain visible in findings (`suppressed: true`) with justification.
- Untrusted PR policy is never auto-trusted (`trusted-policy` loads base ref).
- Clean result ≠ safe component; reports must state what was not tested.

---

## Finding dimensions (keep separate)

| Dimension | Meaning |
| --- | --- |
| Severity | Potential impact |
| Confidence | Strength of evidence / status |
| Exploitability | How realistically reachable |
| Exposure | How accessible the component is |
| Coverage | How much applicable surface was examined |
| Verification | Whether independently established |

Do **not** collapse these into one invented trust score.

A clean scan with 30% coverage is not equivalent to a clean assessment with complete applicable coverage. Missing evidence is never evidence of safety.

---

## Exploitability chain

Every serious finding should establish:

```text
Attacker control
      ↓
Entry point
      ↓
Trust boundary crossed
      ↓
Available capability
      ↓
Missing or ineffective control
      ↓
Security impact
```

If the chain cannot be established, report `POTENTIAL` or an evidence gap — not `CONFIRMED`.

---

## Structured claims (AI auditors)

Before writing the full narrative report, emit intermediate claims:

```json
{
  "claim": "Component can execute local shell commands",
  "status": "OBSERVED",
  "evidence_ids": ["E-001", "E-002"],
  "impact": "Potential local command execution",
  "missing_evidence": [
    "Host execution identity",
    "Effective approval enforcement"
  ],
  "component_ids": ["C-001"]
}
```

Validate report-shaped JSON with the maintainer command:

```bash
auctelis-dev validate report findings.json
```

There is no separate `validate claim` command in this release.

---

## Finding lifecycle (engagements)

```text
NEW → TRIAGED → INVESTIGATING
        → CONFIRMED | REJECTED | INSUFFICIENT EVIDENCE
        → REMEDIATED → REVALIDATED
```

Preserve rejected findings and reasons. Revalidate after changes. Prefer `auctelis watch` for host deltas and `auctelis diff lock` / `auctelis gate` for recurring repo work ([`GUARD-SCAN.md`](GUARD-SCAN.md)).

---

## Report audiences

| Audience | Needs |
| --- | --- |
| Executive | Overall situation, top risks, deployment readiness, required gates |
| Developer | Exact file, what is wrong, how to fix, how to verify |
| Security reviewer | Evidence, attack path, verified vs inferred, residual risk |

Narrative reports are optional operator artifacts. Prefer Guard `findings.json` + `AUTHORITY.lock` as the product source of truth.
