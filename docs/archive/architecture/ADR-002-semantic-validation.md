# ADR-002: Semantic report validation layer

**Status:** Accepted (implemented 2.0.0)  
**Context:** Assessment R-003 — JSON Schema allows structurally valid but untrustworthy reports.  
**Decision:** Add `aesa validate report` with semantic checks after Draft 2020-12 validation: unique IDs, dangling references, findings count reconciliation, CONFIRMED-without-evidence rejection, runtime evidence consistency.  
**Consequences:** Some legacy hand-written JSON may fail until references are fixed. Unknown/false claims are not detected—only structural integrity of the audit record.
