# Common threat scenarios (capability-first)

Every authdiff assessment should evaluate these scenarios. Findings must trace
attacker control → entry → trust boundary → capability → missing control → impact.

Related: [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md), [`SECURITY-RULES.md`](SECURITY-RULES.md),
[`atlas/PRECISION.md`](atlas/PRECISION.md), [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md).

| Scenario | Core security question | Primary rules |
| --- | --- | --- |
| Prompt injection | Can untrusted content cause privileged actions? | RULE-010, RULE-014 |
| Tool poisoning | Can malicious metadata influence tool selection or arguments? | RULE-002, RULE-011 |
| Credential theft | Can components access or transmit sensitive credentials? | RULE-006, RULE-012 |
| Privilege escalation | Can delegated agents acquire excessive authority? | RULE-008, RULE-017 |
| Supply-chain compromise | Can a trusted source deliver an untrusted artifact? | RULE-011, RULE-015 |
| Data exfiltration | Can sensitive information reach unauthorized destinations? | RULE-003, RULE-005, RULE-013 |
| Persistence | Can hooks or automation continue operating unexpectedly? | RULE-004, RULE-007 |
| Approval bypass | Can actions be changed or replayed after approval? | RULE-004, RULE-017 |
| Cross-tenant access | Can identities or memory cross isolation boundaries? | MANUAL_ONLY (memory/RAG) |
| Model compromise | Can model/provider trust affect the security boundary? | MANUAL_ONLY |
| Privileged CI + agent | Can fork PR content reach secrets via agent steps? | RULE-016 |

## Capability-first questions (per component)

- Can it read files?
- Can it write files?
- Can it execute commands?
- Can it access secrets?
- Can it access the network?
- Can it modify agent instructions?
- Can it invoke other tools?
- Can it delegate tasks?
- Can it modify approval decisions?
- Can it access persistent memory?
- Can it operate without a human present?

Then establish which principals and controls govern those capabilities.
