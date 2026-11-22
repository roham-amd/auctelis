# auctelis — CI Authority Diff gate

Product primer for the PR gate. Full product contract: [`PRODUCT.md`](PRODUCT.md).

| Item | Value |
| --- | --- |
| Product release | **0.1.10** |
| Tooling package | **0.1.10** (`auctelis`) |
| Rule pack | **1.6** (research / `auctelis_research` / `auctelis-dev` only) |
| Primary path | `check` → `diff --base` → lockless workflow **or** `init --owner --enforce` → Action / `gate` |
| Policy file | optional `.auctelis.yml` + optional `AUTHORITY.lock` (CODEOWNERS when enforcing) |
| Action | Root `action.yml` (`uses: roham-amd/auctelis@vX`) — **comment-only** default (`locked=false`); legacy subpath still works; `--enforce` / `locked=true` for fail |
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
verdict, at most five ranked cards, the unknowns, and the action. The Action
posts this comment from the tree-truth gate lock delta when authority changed
(base authority is extracted from the base worktree — no committed lock required
for comment-only). The Action is lock-diff only (research annotate inputs were
removed). Inferred doc-link network stays comment-tier; execute / secrets / new
MCP fail only when `locked=true`. Comment-only growth is `NEEDS_REVIEW`, never a
false `PASS`; no-change PRs are quiet unless `comment-on-none: true`.

1. What changed? (`GROWTH` / `REDUCTION` / `NONE`)
2. What new host, launcher, or env key?
3. What is unknown / `NOT PARSED`?
4. What action is required?

Finding IDs and rule IDs stay out of the review UI; they live in the artifacts.

---

## First user journey

```bash
# One-line run without permanent install (see docs/INSTALL.md):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.10#subdirectory=tools" auctelis check                              # aha: ranked reach cards

cd your-repo
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.10#subdirectory=tools" auctelis init --lockless                     # one-file lockless PR Watch (no owner / lock)
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.10#subdirectory=tools" auctelis init --owner security-owner        # full comment-only setup
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.10#subdirectory=tools" auctelis init --owner security-owner --enforce  # optional locked gate
```

Persistent install:

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.1.10#subdirectory=tools"
```

Empty baseline is normal: first growth under enforce is CODEOWNERS review, not
forever `FAIL_CLOSED`.

Recipes:
- Lockless (written by `auctelis init --lockless`): [`../tools/auctelis/templates/auctelis-diff.yml`](../tools/auctelis/templates/auctelis-diff.yml)
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
uses: roham-amd/auctelis@<commit-sha>
# legacy subpath still works:
# uses: roham-amd/auctelis/.github/actions/auctelis-gate@<commit-sha>
```

Or pin the release tag: `@v0.1.10`. The Action fetches the base ref at `--depth=1`
automatically (no `fetch-depth: 0` required) and short-circuits setup in
lockless mode when no watched agent-config or workflow paths changed. Prefer the
root `uses: roham-amd/auctelis@vX` form. Automatic PyPI install on tagged refs runs only when
`AUCTELIS_PYPI_DEFAULT=true` (matches `pypi_live`); until then tagged runs use
bundled `tools/` with no PyPI-404 warning. Explicit `install-tools-from: pypi`
still forces PyPI (with bundled fallback).

### Modes

| Mode | How | Behavior |
| --- | --- | --- |
| **Comment-only** (default) | lockless template / `init` / `locked: false` | Posts Authority Diff as `NEEDS_REVIEW` on tier-1+ growth (tier-0 growth — including plain non-agent CI — stays `PASS` and quiet); check stays green; quiet on `NONE` |
| **Enforce** | `init --enforce` / `locked: true` | Fails on tier≥fail growth, drift, unparsed, missing CODEOWNERS/ruleset |

### Comment policy

- Default `auto`: post only when authority changed (`GROWTH` / `REDUCTION` /
  unparsed / drift). A `NONE` PR gets no new comment; an existing sticky comment
  is updated once to "no authority change". The job summary always records the
  verdict.
- **First run:** when the PR itself adds the Auctelis workflow file (`.github/workflows/auctelis*.yml`)
  and no sticky comment exists yet, a clean install posts one `PASS` "Watching" comment naming the
  reach surfaces. If the same PR also adds other authority (MCP/hook/…), the comment stays
  `NEEDS_REVIEW` and shows those delta cards (the Action never hides smuggled growth behind
  Watching-only). All other no-change PRs stay silent.
- **Walk limits:** default inventory cap is 50 000 kept files / depth 16. Override with
  `AUCTELIS_MAX_FILES` / `AUCTELIS_MAX_DEPTH` or CLI `--max-files`. Truncation fails enforce.
- `comment-on-none: true` (Action) or `gate --comment-policy always` restores a
  comment on every PR (and suppresses the separate first-run comment).
- Default `init --enforce` + local `auctelis status --check` says
  "verify code-owner ruleset in GitHub" instead of failing offline. Use
  `status --check --require-protection` where a missing/UNVERIFIED ruleset must
  fail (for example a CI readiness job).

---

## What auctelis is not

Not a sandbox, not a certification, not a marketplace badge, not a runtime
monitor. Publisher identity stays `NOT VERIFIED`. See [`PRODUCT.md`](PRODUCT.md).
