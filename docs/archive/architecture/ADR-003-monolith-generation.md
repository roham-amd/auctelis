# ADR-003: Monolithic prompt generation

**Status:** Accepted (implemented 2.1.0)  
**Context:** Split kit and monolith drift risk (R-002).  
**Decision:** Generate `archive/methodology/prompts/audit.full.md` from `canonical/prompt/monolithic-header.md`, `01-core-prompt.md` (through §9), `02-modules.md` (§10+), `01-core-prompt.md` (§11–21), `03-report-contract.md` (§22–23), and `01-core-prompt.md` (§24–25). CI fails if monolith hash differs unless regenerated.  
**Consequences:** Edit split kit files, then `aesa build prompts --write`. Monolith is a generated view, not an independent source.
