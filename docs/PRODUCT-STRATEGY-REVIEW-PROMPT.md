# Product strategy review prompt

Copy this prompt to another AI agent when you want a fresh, deep product and
strategy review of **authdiff** on the latest `main` branch.

The reviewer must first understand **what exists today**, then is free to
change **anything** — including deleting the project and starting over.

Related: [`PRODUCT.md`](PRODUCT.md) · [`ROADMAP.md`](ROADMAP.md) ·
[`INSTALL.md`](INSTALL.md) · [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md) ·
[`CHANGELOG.md`](../CHANGELOG.md)

---

You are a product strategist + security-engineering architect reviewing an
open-source project.

## Primary task

1. Fully fetch and understand the **latest** public GitHub repository on `main`
   (or the tag the user names):
   https://github.com/roham-amd/authdiff

2. Do **not** rely on assumptions or outdated memory. Inspect the actual repo
   as deeply as possible. Prefer code, tests, CI, and release metadata over
   marketing prose when they disagree.

3. Only **after** you can accurately describe the current product, produce
   transformative ideas. You have **full creative freedom** — no sacred cows.

## Read order (ground yourself first)

### Contract and version truth
- `VERSION`, `tools/pyproject.toml`, `tools/authdiff/data/VERSION`
- `canonical/versions.json`, `canonical/release-manifest.json`
- `CHANGELOG.md`, GitHub Releases / latest tag
- `docs/PRODUCT.md`
- `docs/ROADMAP.md`
- `docs/INSTALL.md`
- `README.md`

### Gate and operator path
- `docs/AUTHDIFF-GATE.md`
- `docs/AUTHORITY-LOCK.md`
- `docs/CLI-REFERENCE.md`
- `docs/PLAYBOOK.md`
- `docs/POLICY.md`
- `docs/GUARD-SCAN.md`
- `.github/actions/authdiff-gate/`
- `tools/authdiff/templates/authdiff-gate.yml`
- `docs/authdiff-consumer-gate.example.yml`

### Quality / honesty contracts
- `docs/EVIDENCE-MODEL.md`
- `docs/TRUST-AND-SAFETY.md`
- `docs/SECURITY-RULES.md`
- `docs/COVERAGE-MATRIX.md`
- `docs/DOCUMENTATION-INDEX.md`
- `SECURITY.md`, `CONTRIBUTING.md`

### Implementation and proof
- `tools/authdiff/` — especially `cli/`, `gate.py`, `authority_lock.py`,
  `policy.py`, `security/`, `inventory/`, `export/pr_comment.py`, `doctor.py`, `vet.py`
- `skills/authdiff-auditor/`
- `schemas/` (note which schemas code actually validates)
- `examples/demo-vulnerable/`, `examples/attack-replay/`
- `tests/` (what CI runs vs ignores)
- `.github/workflows/`

### Historical only
Treat `archive/`, `docs/archive/`, and stub paths like `kit/` as historical
context — not current product identity — unless you deliberately revive them.

## Commands to run (when the environment allows)

State explicitly if you could not run commands.

```bash
cat VERSION tools/authdiff/data/VERSION
authdiff demo
# Optional:
authdiff doctor
authdiff scan examples/demo-vulnerable -o /tmp/authdiff-out-review
# From tools/ when using uv — note which suites CI ignores:
uv run pytest -q ../tests
uv run authdiff-dev corpus run
```

Also check latest GitHub Actions on `main` and whether the **latest** Release
matches `VERSION`.

## Current product (must internalize before ideation)

Today, authdiff **claims** to be:

> The authority lockfile and PR security gate for AI agents.

Core job to be done (as currently stated):

> Before I install, merge, deploy, or upgrade an AI-agent integration, tell me
> what new authority it introduces, who receives it, and whether that change
> has been approved.

**Intended public loop** (verify against repo; correct if `main` has changed):

`demo → doctor → open/vet → scan/check → lock → gate → ci init`

Claims to verify before you redesign (so you know what you are keeping,
evolving, or killing):

- Deterministic tooling is the source of truth
- An AI agent is an optional explainer, not the primary engine
- The valuable artifact is a short PR Authority Diff + `AUTHORITY.lock`, not a long audit report
- Real CI gate compares against a **base-ref** lock (`gate --base-lock` / Action extract)
- It is **not** (by current contract): certification, marketplace badge, runtime sandbox, or a substitute for organizational risk acceptance
- Version pins, lock **v1**, and docs should agree with `VERSION` / latest release

You may keep that model, evolve it, replace it, or abandon it entirely — but
only after describing the **CURRENT** product accurately (what the repo claims
vs what the code actually does vs what a user gets in 10 minutes).

## Creative freedom (no hard rules)

There are **NO sacred cows**. You may:

- redesign the whole project from scratch
- change its nature completely
- delete the entire repository and propose starting something else
- kill any command, artifact, doc, Action, schema, skill, test suite, or brand
- turn it into a web app, SaaS, CLI, SDK, IDE plugin, Cursor/Claude skill pack,
  MCP server, browser extension, CI action, marketplace, checklist product,
  prompt-only kit, script suite, dataset/benchmark, consulting playbook,
  policy-as-code product, or any hybrid
- narrow the scope dramatically or expand it dramatically
- revive rejected directions (certification, marketplace, runtime sandbox,
  prompt-only audits, etc.) if you justify why the current non-goal is wrong
- propose a completely different job to be done, name, and go-to-market

Prioritize usefulness, adoption, clarity, and real security value over fidelity
to the current architecture.

However (judgment, not rules):

- Do **not** recommend a direction as “new” if it is already substantially
  implemented, unless you propose a material upgrade over what exists.
- Prefer weekly-use products over once-admired frameworks.
- Be honest about what already works (e.g. lock + gate) before you torch it.

## Required response structure

Keep the full response tight and opinionated. Target ≤ 2500 words unless a
point truly needs more detail.

### A. Current-state understanding
Summarize in your own words:
- what authdiff is today (claims vs code vs 10-minute UX)
- version / release / pin consistency
- who it is for
- how it is used end-to-end (local + CI)
- what is strong
- what is weak / confusing / incomplete / overbuilt
- public surface vs `authdiff-dev` / research / archive

Be concrete and cite files. If information is missing, say so — do not invent.

### B. Strategic diagnosis
Answer:
- What is the real product here (if any)?
- What should the “aha” moment be for a first-time user in under 10 minutes?
- What is blocking adoption right now?
- Should this stay tool-operated, become agent-operated, human-operated, or hybrid?
- If you could delete one major surface area next week, what dies — and why?
- Should the project continue at all, shrink hard, or be replaced?

### C. Best redesign directions (ranked)
Give 7–12 distinct product directions, ranked by expected impact × feasibility.
For each direction include:
1. One-sentence pitch
2. Why it is better than the current form (or why starting over wins)
3. Target user
4. Core workflow (5–10 steps max)
5. MVP scope (what to ship first)
6. What to delete/simplify from the current repo (be ruthless)
7. Risks / failure modes
8. Score: Impact / Effort / Differentiation (1–10 each)
9. Novelty note: `already partially built` | `extension of current` | `greenfield` | `replace entirely`

Include at least these families somewhere (plus your own better ones):
- prompt-only audit kit
- Cursor/Claude Code plugin or skill
- MCP server for authority review
- web app for running/reviewing authority diffs
- CI/GitHub Action scanner+report (upgrade or replace the current gate)
- reusable checklist / playbook product
- dataset + benchmark for agent-authority security
- opinionated “one command” CLI
- marketplace / certification-lite workflow
- radical pivot or **delete-and-restart** into something sharper

When you propose killing the current product, say what replaces the weekly habit.

### D. Recommended north-star
Pick **ONE** winning direction (including “delete authdiff and start X”).
Explain why it wins. Then provide:
- crisp product name + one-line positioning (keep authdiff only if it still fits)
- 30-day build plan
- 90-day maturity plan
- minimal architecture
- exact first-user journey
- success metrics (adoption + security value — not vanity)
- explicit kill list from the current repo

### E. Concrete improvements (even if redesign happens)
Regardless of form, list the highest-value improvements to:
- authority / change-control methodology
- evidence model and false-confidence control
- short PR-facing diff usefulness
- module coverage (MCP / skills / hooks / hosts / CI / …)
- operator UX for humans and AI agents
- trust & safety of any gate / review process

Make these specific enough that an engineer could start tomorrow — or clear
enough that they know what **not** to build.

### F. Optional radical alternatives
Give 3 “crazy but serious” pivots (including full-repo replacement).
Each: who pays, why they care weekly, what dies from the current repo.

## Quality bar
- Be specific, opinionated, and practical.
- Prefer bold clarity over polite vagueness.
- Challenge whether the project should remain a large framework at all.
- Optimize for something people would actually use weekly.
- Separate: (1) what the repo claims, (2) what the code does, (3) what users
  understand in 10 minutes.
- Do not invent adoption, customers, or benchmark validity.
- Do not treat archived methodology as the live product unless you revive it on purpose.
- End with a one-paragraph executive recommendation a founder could act on
  immediately — including “stop and replace” if that is your honest answer.
