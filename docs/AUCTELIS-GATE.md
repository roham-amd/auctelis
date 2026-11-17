# auctelis — CI Authority Diff gate

Product primer for the PR gate. Full product contract: [`PRODUCT.md`](PRODUCT.md).

| Item | Value |
| --- | --- |
| Product release | **0.11.0** |
| Tooling package | **0.11.0** (`auctelis`) |
| Rule pack | **1.6** (research / `auctelis_research` / `auctelis-dev` only) |
| Primary path | `diff --base` → lockless workflow **or** `init --owner` → `check` → Action / `gate` |
| Policy file | optional `.auctelis.yml` + optional `AUTHORITY.lock` (CODEOWNERS when enforcing) |
| Action | `.github/actions/auctelis-gate` — **comment-only** default (`locked=false`); `--enforce` / `locked=true` for fail |
| Verdict | `PASS` / `NEEDS_REVIEW` / `BASELINE_ADOPTED` / `FAIL_CLOSED` |
| Label | `GROWTH` / `REDUCTION` / `NONE` (delta shape, not a verdict) |
| Reach tiers | 0 silent · 1 comment · 2 fail (under enforce) |

Normative depth: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md), [`GUARD-SCAN.md`](GUARD-SCAN.md),
[`POLICY.md`](POLICY.md), [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md).

---

## Job to be done

> Before I merge an AI-agent integration, tell me what authority it introduces,
> what data can flow through it, and what materially changed.

The valuable artifact is the **PR Authority Diff comment** (≤12 lines): one
verdict, at most three `old → new` cards, the unknowns, and the action. The
Action always posts this comment from the tree-truth gate lock delta (base
authority is extracted from the base worktree — no committed lock required for
comment-only). Research `annotate: true` is optional enrichment — never a gate
input. Inferred doc-link network stays comment-tier; execute / secrets / new
MCP fail only when `locked=true`.

1. What changed? (`GROWTH` / `REDUCTION` / `NONE`)
2. What new host, launcher, or env key?
3. What is unknown / `NOT PARSED`?
4. What action is required?

Finding IDs and rule IDs stay out of the review UI; they live in the artifacts.

---

## First user journey

```bash
# Git tag is the supported install until PyPI returns the package.
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.11.0#subdirectory=tools"

auctelis diff --base origin/main                # aha (no files written)
# Lockless: copy templates/auctelis-diff.yml → .github/workflows/auctelis.yml
auctelis init --owner security-owner            # comment-only setup
auctelis init --owner security-owner --enforce  # optional locked gate
auctelis check                                  # repo authority vs AUTHORITY.lock
```

Empty baseline is normal: first growth under enforce is CODEOWNERS review, not
forever `FAIL_CLOSED`.

Recipes:
- Lockless: [`../tools/auctelis/templates/auctelis-diff.yml`](../tools/auctelis/templates/auctelis-diff.yml)
- Enforce example: [`auctelis-consumer-gate.example.yml`](auctelis-consumer-gate.example.yml)

### Branch protection / rulesets (when enforcing)

1. Require the `auctelis` workflow job on PRs to the default branch.
2. Require CODEOWNERS review for `AUTHORITY.lock`, `.auctelis.yml`, and
   authority-bearing paths.
3. Enable **dismiss stale pull request approvals when new commits are pushed**.
4. Prefer rulesets; `auctelis gate` labels growth — GitHub enforces the review
   (auctelis does not count PR approvals).
5. Do not allow administrators to bypass required checks on the default branch
   in production repos.

### Secure Action pin (recommended)

Prefer an immutable commit SHA for the Action in high-assurance repos:

```yaml
uses: roham-amd/auctelis/.github/actions/auctelis-gate@<commit-sha>
```

Or pin the release tag: `@v0.11.0`.

### Modes

| Mode | How | Behavior |
| --- | --- | --- |
| **Comment-only** (default) | lockless template / `init` / `locked: false` | Posts Authority Diff; does not fail on growth |
| **Enforce** | `init --enforce` / `locked: true` | Fails on tier≥fail growth, drift, unparsed, missing CODEOWNERS/ruleset |

---

## What auctelis is not

Not a sandbox, not a certification, not a marketplace badge, not a runtime
monitor. Publisher identity stays `NOT VERIFIED`. See [`PRODUCT.md`](PRODUCT.md).
