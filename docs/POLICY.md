# auctelis policy file (`.auctelis.yml`)

Repository-level defaults for the auctelis scan and CI gate.

| Item | Value |
| --- | --- |
| Contract | **1.3** (`require_review` auto-fails matched classes; `NAME_MARKER` never satisfies; schema matches `policy.py`) |
| Local CLI default | Target `.auctelis.yml` is **ignored** unless `--policy PATH` or `--trust-target-policy` (prevents audited repos from suppressing findings) |
| Discovery (when trusted) | Look for `.auctelis.yml` **inside the scan target tree only** (never parent dirs outside the target) |
| CI trust | Action `trusted-policy=true` loads `.auctelis.yml` from the **PR base ref** and fails if an *existing* policy file is edited (first-time add is allowed) |
| Override | Explicit CLI flags always win |
| Disable | `auctelis scan --no-policy` |
| Suppressions | Matching findings are marked `suppressed: true` and retained in artifacts (never deleted) |

## Example

```yaml
version: 1

policy:
  mode: enforce          # advisory | enforce
  fail_on: high          # never | high | any
  output_dir: auctelis-out
  baseline: .auctelis/baseline.json

  require_review:
    - remote_mcp_endpoint
    - privileged_hook
    - credential_access
    - unattended_execution

  ignore:
    - rule: AUCTELIS-RULE-003
      path: examples/**
      justification: "Non-production fixture"
      owner: security-team
      expires: "2027-01-01"
```

Committed example: [`../examples/auctelis.policy.example.yml`](../examples/auctelis.policy.example.yml).

## Semantics

| Field | Behavior |
| --- | --- |
| `mode: enforce` | If `fail_on` is omitted or `never`, Guard raises it to `high` |
| `mode: advisory` | Does not change exit policy by itself |
| `fail_on: high` | Exit 1 on CRITICAL/HIGH `SECURITY_FINDING` or `EXPOSURE` (never pure `CAPABILITY`) |
| `fail_on: any` | Exit 1 on any `SECURITY_FINDING` or `EXPOSURE` |
| `ignore` | Suppress matching findings before gating; each entry **requires** `justification`, `owner`, and `expires` |
| `ignore[].owner` | Accountable human/team for the suppression (required) |
| `ignore[].expires` | Required `YYYY-MM-DD`; expired suppressions are ignored (fail closed) — no forever suppressions |
| `require_review` | **Auto-fails** when a matching finding exists (class → rule/capability map in `review_classes.py`). Independent of `fail_on` severity. `NAME_MARKER` never satisfies a class. |

Gate classes are centralized in `tools/auctelis/security/gating.py`: only
`SECURITY_FINDING` and `EXPOSURE` can block. `CAPABILITY` never blocks under
`fail_on=high|any`, including baseline risk deltas (`gated_findings_added`).

## Finding lifecycle (gates)

| Class | Default CI gate |
| --- | --- |
| `CAPABILITY` | Never blocks unless you build a custom consumer |
| `EXPOSURE` | Blocks under `fail_on: high` when severity is HIGH/CRITICAL, or under `any` |
| `SECURITY_FINDING` | Same as exposure |

Suppressions must not become permanent blind spots: require owner, justification, and preferably an expiration date.

## CLI

```bash
auctelis scan . --policy .auctelis.yml --fail-on high
auctelis scan . --no-policy
```

## Gate integrity

A policy file that the PR author can edit is not a gate. In CI:

1. Set Action input `trusted-policy: true` (default).
2. Checkout with enough history to read the base ref (e.g. `fetch-depth: 0`).
3. Install a pinned auctelis (`pip install …@vX.Y.Z#subdirectory=tools` or
   Action-bundled tools) and set `install-tools-from: path`. Do not let a PR
   supply the scanner under `./tools`.
4. Treat PR edits to `.auctelis.yml` as their own authority-surface change (the
   Action fails closed on those edits when `trusted-policy` is enabled).
