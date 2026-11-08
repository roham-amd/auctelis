<!-- authdiff-authority-diff -->
### authdiff Authority Diff
**Decision:** `BLOCK`
**Changed:** authority could not be fully established
**Authority delta:**
- `F-004` [CRITICAL] Download-and-execute pattern in agent surface (`skills/bootstrap/SKILL\.md:17`)
- +6 more gated findings
**Evidence:** `skills/bootstrap/SKILL\.md:17`, `E-004`, `F-004`, `skills/bootstrap/SKILL\.md:11`
**Risk:** Arbitrary remote code execution
**Confidence:** OBSERVED (runtime not verified)
Unknown: NOT VERIFIED: Runtime behavior, Publisher identity; MANUAL\_ONLY: Browser agents, Memory / RAG
Required: remediate high/critical authority, then re-run gate
Coverage: 17% SUPPORTED \(1/6\); PARTIAL=5 MANUAL\_ONLY=0 — clean result ≠ safe\.
