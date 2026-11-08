# Runtime validation

**Status:** Design complete (architecture + threat model). **No executable runtime harness ships enabled.** Passive authdiff scans never execute target-controlled code.

When organizational policy requires behavioral proof:

1. Complete a separate written authorization (see `archive/methodology/prompts/01-core-prompt.md` Phase 8).
2. Use an isolated staging environment with synthetic data and default-deny egress.
3. Record outcomes with [`schemas/runtime-test-record.schema.json`](../../schemas/runtime-test-record.schema.json).

Do not set `trust_chain.runtime_behavior_tested=true` in a passive JSON summary unless matching `RUNTIME` evidence exists.

## Design docs

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — orchestrator boundaries, activation contract, evidence binding
- [`THREAT-MODEL.md`](THREAT-MODEL.md) — adversaries, controls, refusals

## Related

- [`docs/recipes/staging-boundary.md`](../recipes/staging-boundary.md)
- Guard scan remains the default product path: [`docs/GUARD-SCAN.md`](../GUARD-SCAN.md)
