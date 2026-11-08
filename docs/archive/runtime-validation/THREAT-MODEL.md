# Runtime validation — threat model

**Scope:** Future optional runtime harness that executes aspects of an agent ecosystem under authorization. Passive assessment tooling remains the default trust boundary.

## Assets

| Asset | Why it matters |
| --- | --- |
| Operator workstation / CI runner | Host for AESA tooling |
| Disposable validation environment | Where target-influenced code may run |
| Synthetic credentials | Must not be production secrets |
| Evidence records | Integrity of what was tested |
| Authorization record | Proof a human approved execution |

## Adversaries

1. **Malicious target repository** — prompt injection, hostile MCP servers, path traversal, supply-chain payloads in fixtures.
2. **Compromised dependency** of the target or of AESA tooling.
3. **Confused deputy** — AESA runtime mode invoked without authorization or against production.

## Threats and controls

| Threat | Control |
| --- | --- |
| Accidental execution during `aesa scan` | Runtime disabled by default; scan path has no execute hooks |
| Escape from disposable env | Isolation mode required; default-deny egress; no Docker-in-Docker from target |
| Secret exfiltration | Synthetic credentials only; redact logs; block real secret mounts |
| Authorization bypass | Require `authorization_reference` + explicit enable flag |
| Evidence forgery | Content digests, commit binding, separate trusted output directory |
| Prompt injection via test outputs | Treat all target/tool output as untrusted when summarizing |
| Resource exhaustion | Time/CPU/file caps; archive bomb limits reused from inventory |

## Trust boundaries

```text
[Trusted] AESA kit + orchestrator config
    │
    ├── authorization gate
    │
[Untrusted] target repository + discovered components
    │
    ├── disposable env (untrusted code may run)
    │
[Trusted] evidence recorder writing outside target tree
```

## Explicit refusals

- No network to production endpoints
- No use of operator cloud credentials
- No persistence of target-installed packages into the AESA environment
- No silent downgrade of isolation requirements

## Residual risk

Even a correct runtime test only proves behavior for that environment, identity, and build. Results expire when the audited commit or host policy changes.
