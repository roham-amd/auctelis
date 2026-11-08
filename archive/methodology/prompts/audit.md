# AI AGENT ECOSYSTEM SECURITY AUDIT — v1.0 (kit entry)

This procedure is split into a **kit** to reduce context size and load modules on demand.
Product tooling is **authdiff 3.4** (`aesa scan`); procedure version remains **1.0**.

**Start here:**

0. Prefer deterministic Guard scan first: `aesa scan <target>` — [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md)
1. Operators: [`00-OPERATOR-GUIDE.md`](00-OPERATOR-GUIDE.md) · Docs map: [`../docs/DOCUMENTATION-INDEX.md`](../docs/DOCUMENTATION-INDEX.md)
2. Load guardrails: [`04-passive-guardrails.md`](04-passive-guardrails.md) (Section 1 for every worker)
3. Triage: [`scan-triage.md`](scan-triage.md) or skill [`../skills/authdiff-auditor-compat/SKILL.md`](../skills/authdiff-auditor-compat/SKILL.md)
4. Deep audit (optional): [`01-core-prompt.md`](01-core-prompt.md) + [`02-modules.md`](02-modules.md) + matching [`modules/`](../modules/)
5. Claims + JSON: [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md), [`03-report-contract.md`](03-report-contract.md), [`../schemas/`](../schemas/)

Full monolithic procedure: [`audit.full.md`](audit.full.md)
