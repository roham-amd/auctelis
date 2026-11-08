# ADR-001: Canonical sources and generated artifacts

**Status:** Accepted (implemented 2.0.0)  
**Context:** Assessment R-002 — manual sync between schema aliases and prompt kit caused drift risk.  
**Decision:**  
- Canonical audit report schema: `canonical/schemas/audit-report.schema.json`  
- Published aliases generated/synced to `schemas/`  
- Prompt kit composition declared in `canonical/prompt-kit.manifest.json`  
- Version metadata in `canonical/versions.json` must match root `VERSION`  
**Consequences:** Contributors run `aesa build all` in CI; editing published schemas without updating canonical is rejected.
