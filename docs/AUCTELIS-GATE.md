# auctelis — CI Authority Diff gate

Product primer for the PR gate. Full product contract: [`PRODUCT.md`](PRODUCT.md).

| Item | Value |
| --- | --- |
| Product release | **0.3.4** |
| Tooling package | **0.3.4** (`auctelis`) |
| Rule pack | **1.6** (rules 001–022) |
| Primary path | `doctor` → `lock --home` → `hook install` → (team) Action / `gate` |
| Policy file | `.auctelis.yml` + `AUTHORITY.lock` (CODEOWNERS) on locked upgrade |
| Action | `.github/actions/auctelis-gate` — lockless default; `strict-ruleset` on |
| Verdict | `PASS` / `GROWTH` / `NEEDS_REVIEW` / `BASELINE_ADOPTED` |

Normative depth: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md), [`GUARD-SCAN.md`](GUARD-SCAN.md),
[`POLICY.md`](POLICY.md), [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md).

---

## Job to be done

> Before I install, merge, deploy, or upgrade an AI-agent integration, tell me
> what authority it introduces, who receives that authority, what data can flow
> through it, and what materially changed.

The valuable artifact is the **PR Authority Diff comment** (≤12 lines), answering:

1. What changed?
2. What is the **Authority delta**?
3. What evidence (prefer file:line)?
4. What is unknown / not established?
5. What action is required?

---

## First user journey

```bash
# One-shot aha (PyPI not published yet — git tag/SHA only):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.3.4#subdirectory=tools" auctelis doctor

# Persistent install, then the gate path:
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.3.4#subdirectory=tools"

auctelis doctor                          # host authority map
auctelis lock --home                     # seal host lock
auctelis hook install                    # session delta + PreToolUse
auctelis vet github.com/org/some-skill   # pre-install annotations
# Team: add the lockless Action (locked=false). Upgrade later:
auctelis lock                            # write repo AUTHORITY.lock
auctelis ci init --owner @security-owner # lockless workflow + CODEOWNERS; then locked=true
# auctelis gate --base-lock <base.lock>  # strict-ruleset default on
```

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
    locked: "false"         # lockless-first; set true after AUTHORITY.lock is sealed
    strict-ruleset: "true"  # default: fail growth when ruleset status is UNVERIFIED
```

### Adoption vs growth (do not conflate)

| Situation | Verdict | Meaning |
| --- | --- | --- |
| PR adds first `AUTHORITY.lock`; base has none | `BASELINE_ADOPTED` | Trust ceremony — CODEOWNERS must review the baseline itself |
| Base lock exists; head grows authority | Growth gate `PASS` / `NEEDS_REVIEW` | Compare locks; GitHub enforces owner review |
| Growth + ruleset `OK` | `PASS / protection verified` | Probe confirmed code-owner review requirement |
| Growth + ruleset `UNVERIFIED` | `NEEDS_REVIEW` (default `strict-ruleset`); soft PASS only with `--no-strict-ruleset` | Missing token/API access — not green assurance |
| Growth + ruleset `MISSING` | `NEEDS_REVIEW` | Confirmed absence of code-owner review requirement |

Minimum workflow permissions (example recipe):

```yaml
permissions:
  contents: read
  pull-requests: write   # sticky Authority Diff comment
  security-events: write # SARIF upload when enabled
```

---

## Tamper-resistant behavior

| Control | Behavior |
| --- | --- |
| Trusted policy | On PRs, load `.auctelis.yml` from **base** ref when `trusted-policy: true` |
| First-time policy add | Adding `.auctelis.yml` is allowed; weakening base policy on head fails |
| Lock drift | Action `locked` defaults to **false** (lockless-first); set `true` after sealing `AUTHORITY.lock` |
| Suppressions | Retained in findings (`suppressed: true`), never deleted from evidence |
| Target policy default | Target `.auctelis.yml` ignored unless `--policy` / `--trust-target-policy` |

---

## Hybrid responsibility

| Role | Responsibility | Final decision |
| --- | --- | --- |
| Deterministic tools | Inventory, rules, evidence, lock, SARIF | No |
| AI audit agent | Explanations / remediation proposals | No |
| Human operator | Scope, risk acceptance, lock approval | Yes |

Never ask an LLM to establish a fact a deterministic tool can establish.  
Never let an unsupported LLM interpretation become an enforced finding.  
Never let the agent edit or approve policy without a human.

---

## Interfaces

| Interface | Status |
| --- | --- |
| CLI (`doctor` / `vet` / `scan` / `lock`) | Primary product |
| GitHub Action (trusted policy) | Supported (composite) |
| AI agent skill | Supported (`skills/auctelis-auditor`) |
| Prompt-only kit | Removed in 0.3.0 shrink |
| MCP server assistant | Deferred |
| Web workbench / marketplace | Deferred |

---

## Non-goals (for now)

- Marketplace “certified secure” badges
- SaaS multi-tenant evidence storage
- Bundled runtime detonation harness
- Numeric trust scores that hide coverage gaps
- Claiming detection accuracy without labeled sample counts
