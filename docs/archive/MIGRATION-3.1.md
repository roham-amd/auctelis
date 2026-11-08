# Migrating to authdiff 3.1

From **3.0.x** to **3.1.x** (current: **3.1.1**).

## What changed

| Area | 3.0.x | 3.1.x |
| --- | --- | --- |
| Primary command | `aesa audit --profile quick` | **`aesa scan`** |
| Product name | AESA / AESA Gate | **authdiff** (project still AESA) |
| Deterministic findings | Inventory hints only | Rules `AUTHDIFF-RULE-001`…`010` + SARIF |
| CI Action | Inventory + path diff | Scan mode, `--fail-on`, baseline risk delta, env-safe inputs |
| Auditor skill | Multi-doc attach | Guard-first single workflow + structured claims |
| Versions | Often drifted | `3.1.1` / tooling `0.4.1` aligned via release manifest |
| Finding model | Capability ≈ warning | `CAPABILITY` / `EXPOSURE` / `SECURITY_FINDING` |

Procedure version remains **1.0**. Audit report JSON schema remains **1.0**.

## Operator migration

### Before

```bash
uv run authdiff audit . --profile quick
# attach skill + modules manually
```

### After

```bash
uv run authdiff scan .
uv run authdiff explain F-001 -o authdiff-out
uv run authdiff baseline save -o authdiff-out
# optional deep review with skills/authdiff-auditor-compat
```

`aesa audit` and `aesa preflight` remain supported for handoff packages.

## CI migration

Update consumer workflows:

```yaml
with:
  mode: scan
  fail-on: high
  baseline: .aesa/baseline.json
  # profile only needed if mode: audit
```

See [`authdiff-consumer-gate.example.yml`](authdiff-consumer-gate.example.yml).

## Documentation map

- New: [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md), [`GUARD-SCAN.md`](GUARD-SCAN.md), [`CLI-REFERENCE.md`](CLI-REFERENCE.md), [`SECURITY-RULES.md`](SECURITY-RULES.md), [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md)
- Updated: README, usage, tools README, AUTHDIFF-GATE, skill, SECURITY

## Compatibility notes

- Inventory JSON version field may remain `0.3.0` unless bumped separately; product version is independent.
- SARIF tool name is now **authdiff**.
- Do not treat absence of Guard findings as production approval.
