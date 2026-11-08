# authdiff 3.5 / 3.6.1 implementation backlog

Derived from the November 2026 strategic review (Authority Diff north-star).
Surfaces: **`doctor` + `vet` + `diff` (scan/PR gate)** on one engine.

Status key: `done` · `in_progress` · `next` · `deferred` · `frozen`

## Milestone M — Authority Diff (3.5.0 → 3.6.1)

### M1 Trust and identity

| ID | Deliverable | Status |
| --- | --- | --- |
| M1.1 | Collapse README to one path (doctor → vet → gate) | done |
| M1.2 | Policy discovery stays inside scan target | done |
| M1.3 | Action `trusted-policy` + fail on `.authdiff.yml` PR edits | done |
| M1.4 | Action tools path prefers Action-bundled / pinned kit | done |
| M1.5 | Update GitHub About text + topics away from “prompt kit” | done |
| M1.6 | Publish PyPI + immutable Action tag `v3.6.1` | next |
| M1.7 | Revisit Python ≥3.15 floor | next |
| M1.8 | `kit/` pointer; methodology de-emphasized | done |

### M2 Detection depth

| ID | Deliverable | Status |
| --- | --- | --- |
| M2.1 | Rules 011–016 with positive/negative fixtures | done |
| M2.1b | RULE-017 permission-bypass + RULE-010 content path | done |
| M2.2 | `evidence_strength` + verify/fix hints on findings | done |
| M2.3 | Promote MCP / hooks / host adapters toward SUPPORTED | next |
| M2.4 | Wildcard / auto-approve host permission rule | next (partial via 017) |
| M2.5 | Tool-description poisoning markers | next |
| M2.6 | Labeled corpus precision report (~100 findings) | next (Atlas) |

### M3 Product surfaces

| ID | Deliverable | Status |
| --- | --- | --- |
| M3.1 | `aesa doctor` MVP | done |
| M3.2 | `aesa vet` MVP (URL + local) | done |
| M3.3 | `aesa init-gate` | done |
| M3.4 | Delta-first PR comment (authority N new powers) | done |
| M3.5 | Demo vulnerable repo + PR walkthrough | done |
| M3.6 | Self-contained auditor skill (`uvx`/`uv tool`) | done |
| M3.7 | `--agent` digests + evidence fencing | done |
| M3.8 | `aesa harden` dry-run | done |
| M3.9 | `AUTHORITY.yml` init/verify MVP | done |

### Explicitly deferred / frozen

- Hosted SaaS / shareable web X-ray
- MCP audit-assistant server as a product surface
- Signed attestations / authority lockfile (90-day)
- Runtime canary harness
- Prompt-monolith expansion
- AgentSecBench intake vault / outreach funnel expansion (**frozen** — keep schema)

## Success metrics (from review)

| Metric | Target |
| --- | --- |
| Install → first output | < 2 minutes (`doctor`) |
| First runs with ≥1 non-capability finding | High share on real hosts |
| Blind High/Critical precision | ≥ 90% on ≥100 labeled findings (Atlas) |
| Unsupported `CONFIRMED` claims | 0 |
| Weekly Action repos | ≥ 25 (90-day) |
