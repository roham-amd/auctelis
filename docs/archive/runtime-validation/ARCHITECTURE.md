# Runtime validation — architecture (design only)

**Status:** Architecture and threat model. **No executable runtime harness is enabled by default.** Passive scans never execute target components.

## Goals

Prove selected security properties that static discovery cannot establish, under explicit human authorization, in an isolated environment.

## Non-goals

- Default-on execution of untrusted repositories
- Production traffic or real customer data
- Replacing host IAM
- SaaS orchestration, marketplace certification, or an always-on agent firewall

## Components

```text
Operator authorization record
        │
        ▼
┌───────────────────────────┐
│ Runtime orchestrator      │  (future; disabled by default)
│ - loads authorization     │
│ - selects test plan       │
│ - enforces isolation caps │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Disposable environment    │
│ - synthetic identities    │
│ - mocked services         │
│ - default-deny egress     │
│ - no production secrets   │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Evidence recorder         │
│ - runtime-test-record     │
│ - digests / logs redacted │
│ - links to audit commit   │
└───────────────────────────┘
```

## Activation contract

Runtime validation may run only when **all** are true:

1. Operator supplies a non-empty `authorization_reference`.
2. `AUTHDIFF_RUNTIME_VALIDATION=1` (or equivalent explicit CLI flag) is set — **off by default**.
3. Environment declares `synthetic_data_only=true` and `default_deny_egress=true`.
4. Target execution paths are allowlisted by the test plan (no open-ended shell).

Passive `aesa scan` / `aesa audit` must ignore runtime mode entirely.

## Evidence binding

Successful tests emit `RUNTIME` evidence and `schemas/runtime-test-record.schema.json` records. Passive findings must not be upgraded to `CONFIRMED` solely because a runtime mode exists — only matching runtime evidence may upgrade specific claims.

## Relationship to Guard

| Mode | Executes target? | Primary output |
| --- | --- | --- |
| Passive scan | No | Inventory, capabilities, OBSERVED/POTENTIAL findings |
| AI deep assessment | No (passive) | Structured claims + narrative |
| Runtime validation | Yes, only under authorization | Runtime test records |

See [`THREAT-MODEL.md`](THREAT-MODEL.md) and [`README.md`](README.md).
