# Guard rule-quality pack

Positive, negative, and ambiguous fixtures for deterministic security rules
in pack **1.5** (`AUTHDIFF-RULE-001` … `AUTHDIFF-RULE-022`).

```bash
cd tools && uv run authdiff-dev benchmark rules
# or
cd tools && uv run pytest ../tests/test_rule_quality.py -q
```

Separate from:

- `authdiff-dev benchmark run` — AgentSecBench inventory/rule smoke cases
- `authdiff-dev benchmark llm` — model-agnostic AI submission scoring (offline;
  not independent product validation while external N=0)
- `tests/corpus` — tooling regression corpus
- Focused unit coverage under `tests/test_rules_*.py`
