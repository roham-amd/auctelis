# Ecosystem Atlas

Public precision engine for authdiff detection quality (product priority #2 after
lock/diff correctness). Corpus pass rates are **not** proof of LLM-led audit
effectiveness — only of deterministic rule/adapter behavior.

**Goal:** replace “external N = 0” AgentSecBench ceremony with a labeled sample of
real-world skills, MCP configs, and hook setups — then publish **per-rule precision**
with sample size and confidence, never a single aggregate score that hides weak rules.

## Status

| Item | Status |
| --- | --- |
| Schema for scan + label records | draft (`PRECISION.md`) |
| Local benign + attack fixtures (`tests/atlas/`) | **seeded** (CI: `test_atlas_lite.py`) |
| Crawl harness (`authdiff atlas crawl --demo-seed`) | **shipped** (ledger under `docs/atlas/ledger/`; target N≥300) |
| Crawl of 300–1000 public repos | next (feed seed JSON) |
| Blind label of ~100 findings | next (prefer label quality over raw N) |
| Publish per-rule precision | next (demote gated rules below threshold once N≥100) |
| AgentSecBench intake vault / outreach funnel | **frozen** (keep schema; stop expanding governance) |

## Workflow

1. Crawl → `authdiff scan` → store findings + inventory digests.
2. Sample stratified by rule id and evidence_strength.
3. Blind-label: true positive / false positive / inconclusive / ambiguous.
4. Include negative cases and harmless formatting variants.
5. Publish precision; demote or informational-only rules below ~70% (HIGH/CRITICAL target ≥90% at N≥100); keep `NAME_MARKER` ≤ LOW.

## Responsible disclosure

Aggregate by default. Name individual repos only with coordinated disclosure.
Do not publish secret values from scanned configs.
