# ADR-004: Centralized gate semantics and repository policy

## Status

Accepted (authdiff 3.4) · Extended (3.5 trusted-policy)

## Context

Fail-on checks, PR annotations, risk deltas, and terminal reports each decided
independently which findings were “actionable,” which risked CAPABILITY noise
blocking CI and inconsistent `fail_on=any` behavior with baselines.

Separately, discovering `.authdiff.yml` by walking above the scan target — and
loading the PR head’s policy in CI — let a PR author weaken or disable the gate.

## Decision

1. **`authdiff.security.gating`** is the single source of truth for gate classes
   (`SECURITY_FINDING`, `EXPOSURE`) and exit-code computation.
2. **`.authdiff.yml`** supplies declarative defaults; explicit CLI flags win.
3. Suppressions require justification; optional `expires` fails closed when past.
4. Policy YAML uses a deterministic subset parser (no optional PyYAML) so CI and
   local installs behave identically.
5. `ScanResult.from_findings_doc` rebuilds explain/diff helpers without
   duplicating field mapping in the CLI.
6. **Policy discovery** (3.5) stays inside the scan target tree (`stop_at`); it
   never loads an unrelated parent-directory policy.
7. **CI `trusted-policy=true`** (3.5 Action default) loads `.authdiff.yml` from the
   PR **base ref**, fails if the PR edits `.authdiff.yml`, and installs tooling from
   Action-bundled / pinned kit paths — never silently from a PR-controlled
   workspace `tools/`.

## Consequences

- Adding a new gate class requires updating `gating.py` and tests once.
- CAPABILITY observations remain inventory-only under default policies.
- Consumer workflows must `fetch-depth: 0` (or otherwise have the base ref) for
  trusted policy materialization.
- Extensibility for graph `Relationship` objects remains in `models.py` without
  forcing unused claim dataclasses into the runtime path.
