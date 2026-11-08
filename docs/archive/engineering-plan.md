# AESA engineering plan

Tracks implementation against independent assessments, the [AESA 3.0 product specification](AESA-3.0-PRODUCT-SPEC.md), and the strategic north-star: **authdiff — Authority Diff** (`doctor` / `vet` / `scan` + trusted PR gate).

Authoritative release contract: [`../canonical/release-manifest.json`](../canonical/release-manifest.json).

## Milestone A — Correctness foundation (2.0.0)

| Rec | Status |
| --- | --- |
| R-001 corpus harness | Expanded (CORPUS-001–010) |
| R-002 canonical + CI | Done; monolith parity |
| R-003 semantic validation | Done (report + graph) |

## Milestone B — Architecture (2.0–2.1)

| Rec | Status |
| --- | --- |
| R-004 graph model | Schema + path search + semantic checks |
| R-005 inventory | Skills, MCP, A2A, rules, hooks, plugins, subagents, automations, CI workflows |
| R-006 A2A/multimodal modules | Done |
| R-007 AISVS starter pack | Pilot |

## Milestone C — Interop (2.2)

| Rec | Status |
| --- | --- |
| R-008 SBOM/signature | Digest-only pilot |
| R-009 runtime harness | Schema only — no harness |
| R-011 SARIF | Done (`aesa export sarif`) |
| R-012 recipes | `docs/recipes/` |

## Milestone D — Product experience (2.3–3.0)

| Item | Status |
| --- | --- |
| Bounded collector I/O | Done |
| Native AI skill | Done (`skills/`) |
| Unified `aesa audit` + profiles | Done (3.0.0) |
| Consumer GitHub Action | Done (composite + example) |
| Agent detection benchmark scaffold | Done (`aesa benchmark run`) |
| LLM finding precision/recall runner | Not started |
| PyPI published package | Not started |
| Hosted web workspace | Deferred |

## Milestone E — authdiff (3.1.0)

| Item | Status |
| --- | --- |
| Version consistency + supported 3.x | Done |
| `aesa scan` one-command UX | Done |
| Deterministic rules AUTHDIFF-RULE-001…016 (pack 1.2) | Done |
| Capabilities / evidence / findings model | Done |
| Baselines + risk delta + `--fail-on` | Done |
| Action env-var hardening + SARIF note | Done |
| Structured claim validation | Done |
| AgentSecBench rule expectations (0.2.0) | Done |
| Host / memory / models / browser / CI modules | Done |
| LLM model runner for AgentSecBench | Next |
| PyPI / `uv tool install` distribution | Next |
| Marketplace / SaaS | Deferred |

## Milestone F — Trustworthy continuous gate (3.1.1)

| Item | Status |
| --- | --- |
| Single release manifest (`canonical/release-manifest.json`) | Done |
| Capability vs exposure vs security finding | Done |
| Capability origins (declared / potential / type_default / …) | Done |
| Evidence provenance (digest, commit, line spans) | Done |
| Stable component fingerprints in baselines | Done |
| Rule pack 1.1 severity recalibration | Done |
| Authority-first terminal aha report | Done |
| Policy gates ignore pure CAPABILITY observations | Done |

## Milestone G — Detection quality + hosts (3.2.0)

| Item | Status |
| --- | --- |
| Positive / negative / ambiguous fixtures per rule | Done (`aesa benchmark rules`) |
| AgentSecBench LLM offline scoring runner | Done (`aesa benchmark llm`) |
| Host profiles: Cursor + Claude Code | Done (PARTIAL) |
| Host profile: GitHub Copilot | Done (MANUAL_ONLY) |
| Declared vs effective permissions in inventory | Done |
| Runtime validation architecture + threat model | Done (design only; disabled by default) |

## Milestone H — Baseline trust + measurable AI audits (3.2.1)

| Item | Status |
| --- | --- |
| Fingerprint rename/move integration tests | Done |
| Baseline 1.2 path maps + move vs add/remove | Done |
| AgentSecBench-LLM dataset 0.2.0 (≥8 reviewed cases) | Done |
| Separated detection / evidence / severity / unsupported scores | Done |
| Multi-agent pilot submissions | Done |
| Versioned dataset + rubric docs | Done |

## Milestone I — AgentSecBench validation (3.3.0)

| Item | Status |
| --- | --- |
| Move vs modification vs clone fingerprint regressions | Done (baseline 1.3) |
| Dataset checksums + frozen manifest | Done |
| Public / held-out split | Done |
| Independent review process + adjudication samples | Done |
| External submission schema + offline report | Done |
| Evaluation pin (dataset/rubric/scorer versions) | Done |
| Broad external agent corpus | Open (collection; N=0 at 3.3.1) |
| Live model evaluation harness | Deferred (offline only) |
| IDE / MCP / hosted dashboard | Deferred |

## Milestone J — AgentSecBench external evaluation (3.3.1)

| Item | Status |
| --- | --- |
| Freeze evaluation contract 0.3.0 | Done |
| Submitter package without GT | Done |
| Intake vault + checksums + provenance | Done |
| Held-out integrity (no case-level feedback during collection) | Done |
| Honest external report (not a leaderboard) | Done (N=0 external) |
| Candidate improvements log (no silent 0.3.0 edits) | Done |
| Genuine external submissions | Open — awaiting independent agents |
| Live model / IDE / MCP / SaaS | Deferred |

## Milestone K — Outreach & first independent intakes (post-3.3.1)

| Item | Status |
| --- | --- |
| Participation + outreach guides | Done |
| Collection window + minimum evidence criteria | Done (pre-set) |
| Funnel metrics (`collection-status`) | Done (all zeros) |
| Untrusted-intake hardening | Done |
| First valid independent external intake | Open |
| Diverse set meeting closure minimum (≥3 configs) | Open |
| Feature / IDE / MCP / SaaS release | Deferred until evidence warrants |

## Milestone L — authdiff productization (3.4.0)

North-star (then): local-first scanner + PR change gate. Historical backlog:
[`GUARD-3.4-BACKLOG.md`](GUARD-3.4-BACKLOG.md). **Superseded by Milestone M.**

| Item | Status |
| --- | --- |
| Product identity as Agent Ecosystem Security Gate | Done (3.4.0) |
| Default output outside target tree | Done |
| `.authdiff.yml` policy + suppressions | Done |
| Coverage matrix doc + report adapter table | Done |
| Release-manifest version gate in `aesa build` | Done |
| Pin consumer Action example to release tag | Done |
| Scan-triage prompt + skill simplification | Done |
| Sample Guard scan artifacts | Done |
| `uv tool install` from Git + PyPI OIDC workflow | Done (git) / PyPI awaits trusted publisher |
| Action auto-load `.authdiff.yml` + PR annotations | Done |
| Pilot harness (`aesa pilots run`) | Done |
| First external AgentSecBench intake | Channel open; N=0 |
| Hosted SaaS / marketplace / MCP server | Deferred |

## Milestone M — Authority Diff (3.5.0)

North-star: `doctor` + `vet` + `diff` (scan/PR gate) on one engine. Detailed
backlog: [`GUARD-3.5-BACKLOG.md`](GUARD-3.5-BACKLOG.md).

| Item | Status |
| --- | --- |
| README collapsed to doctor → vet → init-gate → scan | Done |
| `aesa doctor` / `aesa vet` / `aesa init-gate` | Done |
| Policy discovery bounded to scan target | Done |
| Action `trusted-policy` + refuse PR-controlled tools install | Done |
| Rule pack 1.2 (RULE-011…016) + evidence_strength | Done |
| Self-contained auditor skill | Done |
| GitHub About / topics refresh | Done |
| Tag `v3.5.0` + PyPI publish | Next |
| Delta-first PR comment | Next |
| Demo vulnerable repo | Next |
| Hosted SaaS / MCP server / attestations | Deferred |

### Deliberately avoided (next 90 days)

- SaaS dashboard / marketplace / certification badges
- Expanding the prompt framework as the primary investment
- Treating every capability observation as a vulnerability
- Claiming comprehensive security coverage or certification
- Shipping an MCP server that is itself a large new authority surface

## Breaking change policy

- Report contract `audit_version: "1.0"` unchanged through 3.x.
- Findings contract **1.1** adds `finding_class` and richer evidence fields (additive).
- Baseline contract **1.1** adds fingerprints (backward compatible with path keys).
- Product 3.4 keeps Guard `scan` as primary; `audit` remains optional deep assessment.
- Default output directory moves from `<target>/authdiff-out` to cwd `./authdiff-out` (breaking for scripts that assumed target-relative defaults without `-o`).
