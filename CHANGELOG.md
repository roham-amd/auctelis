# Changelog

All notable changes to **authdiff** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

## [0.3.1] — 2026-11-12

### Fixed

- Gate: paginate PR reviews; require approval `commit_id` on PR head; user
  CODEOWNERS must intersect approvers (`OWNER_MISMATCH` otherwise); team-only
  owners mark `approval_enforcement: UNVERIFIED`.
- PR comment: CODEOWNERS rendered as code spans (no blank `[@]` approval line).
- `lock --home` seals **all** present host surfaces (doctor-style staging).
- `ci init` no longer auto-accepts gated findings or invents a human review.
- Claude PreToolUse hook reads stdin JSON, fails closed, does not print approve
  commands into agent context.
- Action: `locked=true` on a PR without a base lock fails closed; `locked=false`
  emits an explicit warning.
- Release workflow requires green validate (lint/mypy/build/pytest) before assets.
- HIGH/CRITICAL gate (and vet REJECT) require `LITERAL_CONFIG`; `INFERRED_HINT`
  capped at MEDIUM for RULE-001 / env-inheritance paths.
- Discover `.claude/commands/**/*.md`; `--version` / `-V`; single public path string.
- Docs: remove stale `@user` matching / advisory-ci / dangling kill-list fragment;
  document that PyPI is not published and `v1.0.0` is superseded.

### Changed

- Product / package version **0.3.1**.
- Runtime dependency surface is `jsonschema` only; `packaging` moved to the
  maintainer `dev` group.
- Prefer `AuthdiffPolicy` type name in the scan path (`AesaPolicy` alias retained).
- Docs and schemas aligned to lock + gate + SBOM (no Agent Authority Manifest CLI).

### Removed

- Unused schemas: `agent-authority-manifest.schema.json`,
  `AI_Agent_Ecosystem_Security_Audit_v1.schema.json` (alias).
- Legacy doc `docs/AGENT-AUTHORITY-MANIFEST.md`.
- Dead version keys: `agent_benchmark*`, `audit_manifest_schema`.

## [0.3.0] — 2026-11-12

### Added

- **Pinned facts** on lock records: `launcher`, `args_digest`, `url_host`, `script_digest`
  (same-name package/launcher swap is a blocking `replacement`).
- `lock --home`, `lock --snapshot`, `lock --resolve` hint; Claude PreToolUse hook template.
- Schema validation on every JSON `AUTHORITY.lock` load (fail closed on malformed).
- Six-scenario gate harness + hostile-lock tests.
- Dogfood: repo `AUTHORITY.lock`, CODEOWNERS, local Action workflow.
- Corpus fixtures `skill-to-mcp-path` / `benign-skill-only` (moved off deleted benchmark tree).

### Changed

- **Gate is the verdict:** `scan --base-lock` is advisory; Action uses `always()` for
  comment/artifacts then fails on scan/gate codes.
- Approval model is **GitHub-native**: any APPROVED PR review counts once base-ref
  CODEOWNERS covers `AUTHORITY.lock` (no homemade `@org/team` login matching).
- Action loads CODEOWNERS from the **base ref**; legacy `mode=audit` removed.
- README leads with `doctor`; public path doctor → lock → gate → ci.
- Kill list: removed `archive/`, `docs/archive/`, `kit/`, `docs/atlas/`, `docs/pilots/`,
  five unused schemas, and research CLI (`benchmark`, `atlas`, `pilots`, `audit`, …).
- Docs and maintainer surface aligned to lock + gate + doctor; CLI reference rewritten.

### Fixed

- `SECURITY.md` / `supported_product_line: 0.x`; `v1.0.0` Release marked superseded.
- Branch-protection / ruleset guidance in `AUTHDIFF-GATE.md`.
- Rebrand debris in the Action PATH check.
- Preflight no longer depends on removed `audit` module; dispatch helpers restored after shrink.

## [0.2.0] — 2026-11-10

### Added

- `authdiff gate --base-lock` — fail on unapproved addition/expansion until a
  CODEOWNERS identity (or GitHub PR approval) is present.
- Action step runs the base-lock gate after the Authority Diff scan.
- `--base-lock` on `scan` / `check` for head-vs-approved-lock deltas.
- Host MCP parsers: Gemini, Zed, opencode, Continue (plus `.claude.json`).
- Attack-replay / benign / flow / evidence-invariant pytest harnesses.
- Atlas labeling template (`docs/atlas/labeling-template.json`) for precision work.

### Changed

- Version label moved to **0.2.0** (pre-1.0) until external adoption justifies 1.x.
- `ci init` requires `--owner`; `lock` requires `--accept-gated` for HIGH/CRITICAL trees.
- Demo always exits 0 and leads with `+/-` lock lines.
- Docs and install recipes pin `@v0.2.0`; wheel-smoke expects demo exit 0.
- Policy type preferred name is `AuthdiffPolicy` (`AesaPolicy` kept as alias).

### Fixed

- Policy YAML parser accepts `ignore: []`, flow lists, and trailing `#` comments
  (day-one `ci init` → `scan --policy` no longer crashes).
- GitHub Action compares head against the **base-ref** `AUTHORITY.lock` via
  `--base-lock` (real authority delta, not head-vs-own-lock).
- PR comment keeps full risk-delta evidence, sorts by severity, shows destination
  hosts, and labels advisory decisions as `ADVISORY (would BLOCK)`.
- `authdiff lock` refuses HIGH/CRITICAL gated trees without `--accept-gated`.
- `authdiff ci init` requires `--owner` (no `@YOUR_TEAM` placeholder).
- Workflow files are no longer double-registered as Automation + CI Workflow.
- Lock seal excludes volatile `repository` path / `audited_commit` (stable hash).
- `authdiff demo` leads with `+/-` lock lines and always exits 0.
- `authdiff doctor` stages `~/.claude` so settings/hooks resolve; parses
  `.claude.json` as MCP config.

## [1.0.0] — 2026-11-09

### Added

- Initial **authdiff 1.0.0** release as a clean product line:
  authority lockfile + PR security gate for AI agents.
- Public CLI: `authdiff` / `authdiff-dev` (package name `authdiff`).
- Core path: `demo` → `doctor` → `vet` → `scan` → `lock` → `ci`.
- `AUTHORITY.lock`, Authority Diff PR comments, GitHub Action gate,
  deterministic rules, and optional coding-agent skill.

### Changed

- Rebranded from the prior AESA / `aesa-tools` product line.
- Policy file: `.authdiff.yml` · artifacts: `authdiff-out/` ·
  Action: `authdiff-gate` · rules: `AUTHDIFF-RULE-NNN`.
- All first-party version surfaces reset to **1.0.0**.
