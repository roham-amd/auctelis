# External submission vault

Append-only intake storage for AgentSecBench-LLM evaluation **0.3.0**.

- `received/<run_id>/` — immutable copies of accepted intake files + `INTAKE.json`
- `REGISTRY.jsonl` — append-only log of all intake attempts

**Only** entries with `provenance: "external"` and `ok: true` count as external evidence.

Templates, samples, and maintainer pilots must **not** be stored here as external.
