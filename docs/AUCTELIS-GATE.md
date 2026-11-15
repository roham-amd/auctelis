# auctelis — CI Authority Diff gate

Product primer for the PR gate. Full product contract: [`PRODUCT.md`](PRODUCT.md).

| Item | Value |
| --- | --- |
| Product release | **0.8.1** |
| Tooling package | **0.8.1** (`auctelis`) |
| Rule pack | **1.6** (rules 001–022) |
| Primary path | `check` → `lock --update` → `ci init --apply --owner` → Action / `gate` |
| Policy file | `.auctelis.yml` + `AUTHORITY.lock` (CODEOWNERS) |
| Action | `.github/actions/auctelis-gate` — **enforce** default (`locked=true`); `--advisory` for warn-only |
| Verdict | `PASS` / `NEEDS_REVIEW` / `BASELINE_ADOPTED` / `FAIL_CLOSED` |
| Label | `GROWTH` / `REDUCTION` / `NONE` (delta shape, not a verdict) |

Normative depth: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md), [`GUARD-SCAN.md`](GUARD-SCAN.md),
[`POLICY.md`](POLICY.md), [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md).

---

## Job to be done

> Before I merge an AI-agent integration, tell me what authority it introduces,
> what data can flow through it, and what materially changed.

The valuable artifact is the **PR Authority Diff comment** (≤12 lines): one
verdict, at most three `old → new` cards, the unknowns, and the action.

1. What changed? (`GROWTH` / `REDUCTION` / `NONE`)
2. What new host, launcher, or env key?
3. What is unknown / `NOT PARSED`?
4. What action is required? (`PASS` / `NEEDS_REVIEW` / `BASELINE_ADOPTED` / `FAIL_CLOSED`)

Finding IDs and rule IDs stay out of the review UI; they live in the artifacts.

---

## First user journey

```bash
# Git tag is the supported install until PyPI returns the package.
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.8.1#subdirectory=tools"

auctelis check                                  # repo authority vs AUTHORITY.lock
auctelis lock --update                          # seal (empty baseline OK)
auctelis ci init --apply --owner @security-owner  # CODEOWNERS + ruleset verify
# auctelis gate --base-lock <base.lock>         # strict-ruleset default on
```

Empty baseline is normal: first growth is CODEOWNERS review, not forever
`FAIL_CLOSED`. Use `lock --accept-gated` only for intentional seals of trees
with HIGH/CRITICAL annotations (records no approval).

Single CI recipe: [`auctelis-consumer-gate.example.yml`](auctelis-consumer-gate.example.yml).

### Branch protection / rulesets (required)

Treat the Action like a dependency lock gate:

1. Require the `auctelis` workflow job on PRs to the default branch.
2. Require CODEOWNERS review for `AUTHORITY.lock`, `.auctelis.yml`, and
   authority-bearing paths (`**/.mcp.json`, `**/.cursor/mcp.json`, hooks, skills).
3. Enable **dismiss stale pull request approvals when new commits are pushed**.
4. Prefer rulesets over legacy branch-protection when available; include team
   owners there. `auctelis gate` labels GROWTH vs REDUCTION and requires
   CODEOWNERS coverage plus a best-effort ruleset check — GitHub enforces the
   human review (auctelis does not count PR approvals).
5. Do not allow administrators to bypass the required checks on the default branch
   in production repos.

### Secure Action pin (recommended)

Prefer an immutable commit SHA for the Action in high-assurance repos:

```yaml
- uses: roham-amd/auctelis/.github/actions/auctelis-gate@<commit-sha>
  with:
    trusted-policy: "true"
    authority-diff: "true"
    locked: "true"
    strict-ruleset: "true"
```

---

## Modes

| Mode | How | Behavior |
| --- | --- | --- |
| **Enforce** (default) | `ci init` / `locked: true` | Lock drift fails; growth needs CODEOWNER |
| **Advisory** | `ci init --advisory` / `locked: false` | Posts diff; does not fail on lock drift |

---

## Related

- Local preflight: `auctelis check`
- Lock format: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md)
- Playbook: [`PLAYBOOK.md`](PLAYBOOK.md)
