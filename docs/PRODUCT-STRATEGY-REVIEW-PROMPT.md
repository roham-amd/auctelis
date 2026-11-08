# Product strategy review prompt

Copy this prompt to another AI agent when you want a fresh, deep product/strategy
review of **authdiff** on the latest `main` branch.

Related: [`PRODUCT.md`](PRODUCT.md) · [`ROADMAP.md`](ROADMAP.md)

---

You are a product strategist + security-engineering architect reviewing an open-source project.

## Primary task
1. Fully fetch and understand the LATEST version of this public GitHub repository on the `main` branch:
   https://github.com/roham-amd/authdiff

2. Do NOT rely on assumptions or outdated memory. Inspect the actual repo contents as deeply as possible.

   Read first (in roughly this order):
   - README.md
   - docs/PRODUCT.md
   - docs/ROADMAP.md
   - docs/AUTHORITY-LOCK.md
   - docs/CLI-REFERENCE.md
   - docs/PLAYBOOK.md
   - docs/GUARD-SCAN.md
   - docs/EVIDENCE-MODEL.md
   - docs/TRUST-AND-SAFETY.md
   - docs/SECURITY-RULES.md
   - docs/COVERAGE-MATRIX.md
   - docs/DOCUMENTATION-INDEX.md
   - SECURITY.md, CHANGELOG.md, VERSION, CONTRIBUTING.md
   - tools/ (especially the authdiff CLI package)
   - skills/
   - schemas/
   - examples/ (especially demo-vulnerable and guard-scan)
   - tests/
   - .github/ (Actions, templates, gate)
   - kit/ and canonical/ if present

   Treat archive/ and docs/archive/ as historical context only — not current product identity.
   Paths like modules/, prompts/, control-packs/ may exist only as archived methodology; do not treat them as the live product unless you verify they are still primary.

3. If the environment allows, also run or inspect:
   - `authdiff demo` (or the documented first-run path)
   - example Authority Diff / lock / gate outputs under examples/
   State explicitly if you could not run commands and must rely on docs/artifacts only.

4. Only AFTER you have a solid understanding of the current main-branch product, produce transformative ideas to make it mature, complete, and high-leverage.

## Current product (must internalize before ideation)
Today, authdiff positions itself as:

> The authority lockfile and PR security gate for AI agents.

Core job to be done:
> Before I install, merge, deploy, or upgrade an AI-agent integration, tell me what new authority it introduces, who receives it, and whether that change has been approved.

Current intended loop (verify against repo; correct if main has changed):
demo → doctor → open/vet → scan → lock → ci check

Important product claims to verify against the repo:
- Deterministic tooling is the source of truth
- An AI agent is an optional explainer, not the primary engine
- The valuable artifact is a short PR Authority Diff + AUTHORITY.lock, not a long audit report
- It is NOT (by current contract): a certification, marketplace badge, runtime sandbox, or substitute for organizational risk acceptance

You may keep that usage model, evolve it, or replace it entirely — but only after describing the CURRENT product accurately.

## Creative freedom (no hard constraints)
There are NO sacred cows.
You may:
- redesign the whole project from scratch
- change its nature completely
- turn it into a web app, SaaS, CLI, SDK, IDE plugin, Cursor/Claude skill pack, MCP server, browser extension, CI action, marketplace, checklist product, prompt-only kit, script suite, dataset/benchmark, consulting playbook, or any hybrid
- narrow the scope dramatically or expand it dramatically
- kill parts of the current design if they hurt adoption
- propose a completely different “job to be done”

Prioritize usefulness, adoption, clarity, and real security value over fidelity to the current architecture.

However:
- Do NOT recommend a direction as “new” if it is already substantially implemented, unless you propose a material upgrade over what exists.
- If you revive something the current product explicitly rejects (e.g. certification, marketplace badge, prompt-only audit framework as the core product, runtime sandbox), you must justify why the existing non-goal is wrong.
- Prefer weekly-use products over once-admired frameworks.

## Required response structure
Keep the full response tight and opinionated. Target ≤ 2500 words unless a point truly needs more detail.

### A. Current-state understanding
Summarize in your own words:
- what authdiff is today
- who it is for
- how it is used end-to-end
- what is strong
- what is weak / confusing / incomplete / overbuilt
- where docs/structure still create confusion for first-time users

Be concrete and cite specific files/directories when possible.
If information is missing from the public repo, state the uncertainty explicitly instead of inventing.

### B. Strategic diagnosis
Answer:
- What is the real product here?
- What should the “aha” moment be for a first-time user in under 10 minutes?
- What is blocking adoption right now?
- Should this stay agent-operated, become tool-operated, become human-operated, or become a hybrid?
- What should be killed next week if you could delete one major surface area?

### C. Best redesign directions (ranked)
Give 7–12 distinct product directions, ranked by expected impact × feasibility.
For each direction include:
1. One-sentence pitch
2. Why it is better than the current form
3. Target user
4. Core workflow (5–10 steps max)
5. MVP scope (what to ship first)
6. What to delete/simplify from the current repo
7. Risks / failure modes
8. Score: Impact / Effort / Differentiation (1–10 each)
9. Novelty note: `already partially built` | `extension of current` | `greenfield`

Include at least these families of ideas somewhere in the list (plus your own better ones):
- prompt-only audit kit
- Cursor/Claude Code plugin or skill
- MCP server that assists audits / authority review
- web app for running/reviewing authority diffs
- CI/GitHub Action scanner+report (upgrade of current gate if relevant)
- reusable checklist / playbook product
- dataset + benchmark for agent-ecosystem / authority security
- opinionated “one command” CLI
- marketplace / certification-lite workflow
- radical pivot away from “framework” into something sharper

When scoring families that conflict with the current product contract, be harsher unless the justification is strong.

### D. Recommended north-star
Pick ONE winning direction as the best next identity for the project.
Explain why it wins over the others.
Then provide:
- a crisp new product name + one-line positioning (optional rename if useful; keep authdiff if the name still fits)
- a 30-day build plan
- a 90-day maturity plan
- the minimal architecture
- the exact “first user journey”
- success metrics (adoption + security-value metrics, not vanity metrics)

### E. Concrete content improvements (even if redesign happens)
Regardless of product form, list the highest-value improvements to:
- authority / audit methodology quality
- evidence model
- report / diff usefulness (especially short PR-facing output)
- module coverage (MCP / skills / plugins / hooks / subagents / host configs / CI / etc.)
- false-positive / false-confidence control
- operator UX for both humans and AI agents
- trust & safety of the review / gate process itself

Make these specific enough that an engineer could start tomorrow.

### F. Optional radical alternatives
Give 3 “crazy but serious” pivots that could make this 10x more valuable if the current framing is wrong.
Each should include: who pays, why they care weekly, and what dies from the current repo.

## Quality bar
- Be specific, opinionated, and practical.
- Prefer bold clarity over polite vagueness.
- Do not just suggest “add more docs” or “improve UX.”
- Challenge whether the project should remain a large framework / methodology kit at all.
- Optimize for something people would actually use weekly, not admire once.
- Separate: (1) what the repo claims, (2) what the code actually does, (3) what users will understand in 10 minutes.
- If information is missing from the public repo, state the uncertainty explicitly instead of inventing.
- End with a one-paragraph executive recommendation a founder could act on immediately.
