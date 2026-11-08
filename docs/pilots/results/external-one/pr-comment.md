<!-- authdiff-authority-diff -->
### authdiff Authority Diff
**Decision:** `BLOCK`
**Changed:** absolute head scan
**New authority:**
- `F-013` [HIGH] pull\_request\_target workflow invokes agent-related steps (`\.github/workflows/revision\.yml`)
**Evidence:** `E-013`, `F-013`
Unknown: NOT VERIFIED: Runtime behavior, Publisher identity; MANUAL\_ONLY: Browser agents, Memory / RAG
Required: remediate high/critical authority, then re-run gate
Coverage: 13% SUPPORTED \(2/15\); PARTIAL=13 MANUAL\_ONLY=0 — clean result ≠ safe\.
