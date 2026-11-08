# Recipe — Authority Diff first assessment (recommended default)

Use this pattern for most developers and repos that may contain Skills, MCP
configs, hooks, or other agent surfaces.

## Goal

Produce a non-empty, evidence-backed authority picture in under 10 minutes, then
optionally deepen with an AI auditor and wire a tamper-resistant CI gate.

## Steps

1. **Install**
   ```bash
   uv tool install "git+https://github.com/YOUR_GITHUB_ORG/authdiff.git@v3.6.1#subdirectory=tools"
   ```
2. **Host map** — `aesa doctor` (local-only; usually non-empty).
3. **Pre-install check (optional)** — `aesa vet github.com/org/candidate` or a local path.
4. **Authorize repo scope** — confirm path/commit, data sensitivity, passive mode.
5. **Scan**
   ```bash
   authdiff scan /path/to/target -o /path/to/work/authdiff-out
   ```
6. **Triage** — read `scan-summary.txt`; prefer `SECURITY_FINDING`/`EXPOSURE` and
   `evidence_strength: LITERAL_CONFIG`; open items with `aesa explain F-00N`.
7. **Baseline** — `aesa baseline save -o …/authdiff-out` for future diffs.
8. **Gate** — `aesa init-gate` then pin the kit ref; keep `trusted-policy: true`.
9. **Deep review (optional)** — attach `skills/authdiff-auditor-compat`; load only matching modules.
10. **Claims / report (optional)** — structured claims + `aesa validate claim|report`.

## Expected outputs

- Host authority map and/or deterministic findings with file evidence
- Explicit NOT VERIFIED coverage gaps
- CI workflow that loads policy from the PR base ref

## Non-goals

- Declaring the repository or host “secure”
- Executing target code or contacting MCP endpoints in passive mode

See also: [`../GUARD-SCAN.md`](../GUARD-SCAN.md), [`../AUTHDIFF-GATE.md`](../AUTHDIFF-GATE.md),
[`small-repo-deep-audit.md`](small-repo-deep-audit.md).
