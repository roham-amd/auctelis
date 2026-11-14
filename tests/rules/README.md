# Guard rule fixtures

Positive, negative, and ambiguous fixtures for deterministic security rules
in pack **1.6** (`AUCTELIS-RULE-001` … `AUCTELIS-RULE-022`).

```bash
cd tools && uv run pytest ../tests/test_rule_case_manifests.py ../tests/test_rules_011_016.py ../tests/test_workflow_rule_calibration.py -q
```

`tests/rules/cases/*.json` is now a live parametrized suite: each manifest names
a fixture and the expected firing, class, severity, and evidence strength.

Separate from:

- `tests/corpus` — tooling regression corpus
- `tests/atlas` — mini benign/attack gate fixtures
- Focused unit coverage under `tests/test_rules_*.py` and related scan tests
