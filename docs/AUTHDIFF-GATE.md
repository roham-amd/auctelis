# authdiff — CI Authority Diff gate

Product primer for the PR gate. Full product contract: [`PRODUCT.md`](PRODUCT.md).

| Item | Value |
| --- | --- |
| Product release | **0.3.2** |
| Tooling package | **0.3.2** (`authdiff`) |
| Rule pack | **1.6** (rules 001–022) |
| Primary path | `authdiff doctor` → `lock` → `scan/gate` → `ci init --owner` / Action |
| Policy file | `.authdiff.yml` + `AUTHORITY.lock` (CODEOWNERS) |
| Action | `.github/actions/authdiff-gate` (display name: authdiff) |
| Verdict | `authdiff gate` (scan `--base-lock` is advisory) |

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
uvx --from "git+https://github.com/roham-amd/authdiff.git@v0.3.2#subdirectory=tools" authdiff demo

# Persistent install, then the gate path:
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/authdiff.git@v0.3.2#subdirectory=tools"

authdiff doctor                          # host authority map
authdiff vet github.com/org/some-skill  # pre-install verdict
authdiff scan .                          # bare `authdiff` also defaults to scan .
authdiff lock                            # write AUTHORITY.lock (--accept-gated if needed)
authdiff ci init --owner @security-owner
authdiff check --locked .
# On PRs the Action compares head to the base-ref lock and runs:
# authdiff gate --base-lock <base-AUTHORITY.lock>
# scan --base-lock only writes the delta; gate is the merge verdict.
```

Single CI recipe: [`authdiff-consumer-gate.example.yml`](authdiff-consumer-gate.example.yml).

### Branch protection / rulesets (required)

Treat the Action like a dependency lock gate:

1. Require the `authdiff` workflow job on PRs to the default branch.
2. Require CODEOWNERS review for `AUTHORITY.lock`, `.authdiff.yml`, and
   authority-bearing paths (`**/.mcp.json`, `**/.cursor/mcp.json`, hooks, skills).
3. Enable **dismiss stale pull request approvals when new commits are pushed**.
4. Prefer rulesets over legacy branch-protection when available; include team
   owners there. `authdiff gate` labels GROWTH vs REDUCTION and requires
   CODEOWNERS coverage plus a best-effort ruleset check — GitHub enforces the
   human review (authdiff does not count PR approvals).
5. Do not allow administrators to bypass the required checks on the default branch
   in production repos.

### Secure Action pin (recommended)

Prefer an immutable commit SHA for the Action in high-assurance repos:

```yaml
- uses: roham-amd/authdiff/.github/actions/authdiff-gate@<commit-sha>
  with:
    trusted-policy: "true"
    authority-diff: "true"
    locked: "true"   # first-lock adoption PR is allowed; later PRs need base lock
```

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
| Trusted policy | On PRs, load `.authdiff.yml` from **base** ref when `trusted-policy: true` |
| First-time policy add | Adding `.authdiff.yml` is allowed; weakening base policy on head fails |
| Lock drift | Action `locked` defaults to **true**; fails when observed authority ≠ `AUTHORITY.lock` |
| Suppressions | Retained in findings (`suppressed: true`), never deleted from evidence |
| Target policy default | Target `.authdiff.yml` ignored unless `--policy` / `--trust-target-policy` |

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
| AI agent skill | Supported (`skills/authdiff-auditor`) |
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
