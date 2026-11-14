# auctelis security regression corpus (v0.3)

Pilot ground-truth cases for **deterministic tooling** (inventory adapters, validators, graph helpers, digest/SARIF pilots). LLM procedure effectiveness is **not** fully benchmarked by this harness yet — do not cite corpus pass rates as detection quality for model-led audits.

## Layout

- `fixtures/` — synthetic miniature repositories (benign, vulnerable, ambiguous cases expand over time).
- `cases/` — case manifests referencing fixtures and expected validator outcomes (`CORPUS-001` … `CORPUS-010`).
- `../validation/` — shared positive/negative JSON fixtures for schema and semantic validation.

## Run

```bash
cd tools && uv sync --locked
auctelis-dev corpus run
```

## Ground-truth rules

1. Expected results must be derivable from fixture bytes visible to the auditor.
2. Each case lists negative expectations (what must not be claimed) as the corpus matures.
3. Adversarial cases use inert payloads only — no live exploits or secrets.

## Current coverage

| Case | Validates |
| --- | --- |
| CORPUS-001 | Passive inventory adapters (Skill + MCP config) |
| CORPUS-002 | Report JSON Schema + semantic validation (positive) |
| CORPUS-003 | Semantic validator rejects orphan evidence |
| CORPUS-004 | Ecosystem graph JSON Schema |
| CORPUS-005 | Prompt-injection skill inventory fixture |
| CORPUS-006 | A2A Agent Card discovery |
| CORPUS-007 | Attack path search helper |
| CORPUS-008 | Digest verify helper |
| CORPUS-009 | Duplicate component id rejection |
| CORPUS-010 | SARIF export pilot |

## Explicit non-goals (today)

- Measuring recall/precision of AI audit agents
- Full SBOM / signature verification
- Runtime detonation or live MCP endpoint testing
