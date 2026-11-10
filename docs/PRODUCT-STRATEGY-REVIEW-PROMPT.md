# Product status review prompt

Copy this prompt to another AI agent when you want an accurate, evidence-based
**status assessment** of **authdiff** on the latest `main` branch (or a named
tag). This prompt is for judging **what the project is today** — health,
contract fidelity, adoption blockers — **not** for inventing a new product.

Related: [`PRODUCT.md`](PRODUCT.md) · [`ROADMAP.md`](ROADMAP.md) ·
[`INSTALL.md`](INSTALL.md) · [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md) ·
[`CHANGELOG.md`](../CHANGELOG.md)

---

You are a product + security-engineering reviewer assessing an open-source
project's **current status**. Optimize for truthfulness over politeness.

## Primary task

1. Fully fetch and understand the **latest** public GitHub repository on `main`
   (or the tag the user names):
   https://github.com/roham-amd/authdiff

2. Do **not** rely on assumptions or outdated memory. Inspect the actual repo.
   Prefer code, tests, CI, and release metadata over marketing prose when they
   disagree.

3. Produce a **status judgment only**. Do **not** propose redesigns, pivots,
   renames, SaaS plans, or new product directions unless the user explicitly
   asks in a follow-up. If something is broken or off-contract, say so and
   name the smallest fix — not a new identity.

## Read order (required)

Read these first, then go deeper as needed:

### Contract and version truth
- `VERSION`, `tools/pyproject.toml`, `tools/authdiff/data/VERSION`
- `canonical/versions.json`, `canonical/release-manifest.json` (and wheel copies under `tools/authdiff/data/`)
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
- `schemas/` (note which schemas are actually validated in code)
- `examples/demo-vulnerable/`, `examples/attack-replay/`
- `tests/` (and which suites CI runs vs ignores)
- `.github/workflows/` (validate, release, publish)

### Historical only
Treat `archive/`, `docs/archive/`, and stub paths like `kit/` as **historical
context**, not current product identity. Do not treat methodology kits,
prompt packs, or certification language as live product unless code + docs
still make them primary.

## Commands to run (when the environment allows)

State explicitly if you could not run commands.

Preferred checks (adjust paths for a clone):

```bash
# Version parity
cat VERSION tools/authdiff/data/VERSION
# Demo aha (must exit 0 on current product path)
authdiff demo
# Optional local loop smoke
authdiff doctor
authdiff scan examples/demo-vulnerable -o /tmp/authdiff-out-status
# Dev validation (from tools/ when using uv)
uv run ruff check authdiff
uv run mypy authdiff
uv run pytest -q ../tests --ignore=../tests/test_benchmark_governance.py \
  --ignore=../tests/test_benchmark_intake.py --ignore=../tests/test_benchmark_llm.py
uv run authdiff-dev corpus run
uv run authdiff-dev build all
```

Also inspect latest GitHub Actions on `main` and whether the **latest** Release
matches `VERSION` (assets: wheel, sdist, SBOM if claimed).

## Current product contract (verify — do not assume)

Positioning to check against the repo:

> The authority lockfile and PR security gate for AI agents.

Job to be done:

> Before I install, merge, deploy, or upgrade an AI-agent integration, tell me
> what new authority it introduces, who receives it, and whether that change
> has been approved.

**Intended public loop** (correct if `main` differs — cite evidence):

`demo → doctor → open/vet → scan/check → lock → gate → ci init`

Claims to verify (pass / fail / partial with file citations):

| Claim | What “pass” looks like |
| --- | --- |
| Deterministic tooling is source of truth | Scan/lock/gate work without an LLM |
| Agent is optional explainer | Skill/docs refuse mutating paths under `AUTHDIFF_AGENT` |
| Valuable artifact is short PR Authority Diff + `AUTHORITY.lock` | PR comment + lock are primary; long audit is secondary/archive |
| Real CI gate vs base lock | Action extracts base-ref lock; `gate --base-lock` / scan `--base-lock` |
| Not certification / marketplace / runtime sandbox | Docs and roadmap keep these non-goals |
| Version pins match release | README/INSTALL/templates pin the same tag as `VERSION` |
| Lock schema matches docs | `AUTHORITY.lock` **v1** everywhere (not stale “v2”) |
| Policy day-one works | `ci init --owner` + `ignore: []` parse; no placeholder `@YOUR_TEAM` left |
| Public vs maintainer surface | Core six + `ci` are clear; `authdiff-dev` / benchmark / atlas do not block the product loop |

## Required response structure

Keep the response tight and evidence-based. Target ≤ 2000 words.

### A. Version and release status
- Declared version(s) and whether they are consistent across manifests
- Latest git tag / GitHub Release / whether it is marked latest
- Install pins in README/INSTALL/Action templates vs actual tag
- Any skew (docs, wheel metadata, Action `@v…`)

### B. Product identity (as implemented)
In your own words, with file citations:
- What authdiff **is** today
- Who it is for
- End-to-end operator path (local + CI)
- What is in-scope vs explicitly out-of-scope
- Public CLI surface vs hidden / `authdiff-dev` / research surface

### C. Contract fidelity scorecard
Score each row **Pass / Partial / Fail / Unknown**, with one-line evidence:

1. Demo aha (`demo` exit behavior, `+/-` lock lines)
2. Doctor / host map usefulness
3. Pre-install `open`/`vet`
4. Scan findings + SARIF + short report
5. `AUTHORITY.lock` write/check/diff (v1 seal stability)
6. `gate --base-lock` + CODEOWNERS / approval model
7. GitHub Action base-ref lock + locked mode
8. Policy (`.authdiff.yml`) trust rules and parse robustness
9. Evidence / coverage honesty (`SUPPORTED` / `PARTIAL` / …)
10. Docs accuracy (no contradictory version/lock/command guidance)
11. Agent skill thinness (explain-only)
12. Test + CI proof for the product path

### D. Strengths
Bullet list of what is genuinely strong **right now** (cite proof).

### E. Gaps, risks, and confusion
Prioritized list of what is weak, incomplete, overbuilt, or confusing for a
first-time user. Separate:
1. **Broken / failing** (must fix)
2. **Off-contract / misleading** (docs or UX lie)
3. **Debt / overbuild** (safe to defer)
4. **Unknown** (could not verify)

Call out specifically if full `pytest` without ignores fails while CI ignores
suites (e.g. benchmark) — do not hide that.

### F. Adoption blockers (next 30 days)
Top 5 concrete blockers to weekly use by a real team, ranked. Each item:
problem → evidence → smallest fix (not a redesign).

### G. Status verdict
One clear overall rating:

| Rating | Meaning |
| --- | --- |
| **Production-ready (narrow)** | Core lock+gate path works; pins/docs/CI agree; known non-goals held |
| **Usable preview** | Core path works with caveats; docs or edge paths still drift |
| **Research / incomplete** | Primary claims not backed by working gate/tests/release |
| **Confused identity** | Docs, code, and packaging tell different stories |

Then:
- **One-paragraph executive status** a founder can trust
- **Top 3 actions this week** (smallest high-leverage fixes only)

## Quality bar
- Separate: (1) what the repo **claims**, (2) what the **code** does, (3) what a
  user understands in **10 minutes**.
- Cite paths, commands, workflow names, and version strings.
- Do not invent adoption, customers, or benchmark validity.
- Do not recommend “add more docs” without naming the contradiction to fix.
- Do not treat archived methodology as the product.
- Do not propose a new product vision in this review.
- If information is missing from the public repo, say **Unknown** — do not invent.
