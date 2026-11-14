# Changelog

All notable changes to **Auctelis** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [0.5.0] — 2026-11-14

### Added

- First-run screen shows **new destinations / executables / secrets** only;
  remaining records collapse behind an inventory line (exit `0` until sealed).
- `auctelis why <name>` prints the exact config path and reach fields.
- Hook **heartbeat** + 5-entry delta ledger; `hook status` distinguishes
  `wired, not yet observed` from `firing (last: …)`.
- `docs/REACH.md` — one-page reach definition for lock schema v1.
- Watch JSON reports include `schema_version: watch-report/1`.
- Win/macOS pytest matrix job for the product path.

### Changed

- Public path: `watch → --seal → --arm → why → hook status` (gate/ci demoted
  from default help; still callable).
- PreToolUse hooks documented as **tripwires**, not enforcement/sandbox.
- North-star copy unified to “can **reach**” (README / parser / release manifest).
- `CORE_PUBLIC_COMMANDS` drops `gate` / `ci`; adds `why`.
- Package description and module docstring match the lockfile product.

### Fixed

- Empty home no longer claims both “no host config” and “every record is new”.

## [0.4.0] — 2026-11-14

### Added

- `auctelis watch`: one-screen declared authority delta against
  `~/.auctelis/AUTHORITY.lock`, with one card per change
  (`+ mcp "linear" → mcp.linear.app · network · tools · unpinned · publisher NOT VERIFIED`).
- `watch --seal` (human baseline), `watch --arm` (hooks), `--delta-only`, `--json`.
- Cursor hooks: `~/.cursor/hooks.json` (`sessionStart`, `beforeMCPExecution`,
  `beforeShellExecution`, `beforeFileEdit`), plus `auctelis_cursor_hook.py`.
- `auctelis hook status`: wired / not firing / not armed per host.
- 54 rule-case manifests are now a live parametrized regression suite.
- Fail-closed tests for unparsed configs, missing/corrupt locks, and `mcp_tools`
  diffs.

### Security / reliability

- `auctelis gate` now fails closed (`NEEDS_REVIEW`) when head configs cannot be
  parsed, even when a trusted `--head-lock` is supplied.
- Missing base or head lock files return `FAIL_CLOSED` instead of a traceback or
  a silent re-scan.
- `AUTHORITY.lock` loading rejects truncated/garbage JSON instead of falling
  back to an empty YAML lock.
- `mcp_tools` additions/removals/digest changes are part of the authority delta.
- Hook install backs up corrupt Claude/Cursor settings before rewriting, and
  refuses when `AUCTELIS_AGENT=1`.
- Session hook reconfigures stdout to UTF-8 so Windows pipes cannot crash it.
- Locks and JSON artifacts are written with LF newlines.

### Changed

- Bare `auctelis` runs `watch`, never a scanner.
- `doctor` and `doctor --since-lock` render the same one-screen delta; the
  findings wall is gone.
- Claude PreToolUse matcher is `.*`; `mcp__server__tool` calls now reach the
  allowlist and known servers are allowed.
- `scan`, `check`, `vet`, `explain`, `harden`, and SARIF are hidden from default
  help (still callable).
- PR comment: one verdict line (`PASS` / `NEEDS_REVIEW` / `BASELINE_ADOPTED` /
  `FAIL_CLOSED`), at most three old → new cards, no finding IDs, and
  `NOT PARSED` in the unknown line.
- Release manifest: `locked_action_default: false`, `primary_command:
  auctelis watch`, verdict/label language separated.
- First install block everywhere is the git tag; PyPI is not the command today.
- Architecture: host staging moved to `host_scan.py`; CLI guards/handlers split;
  shared `delta_label`; `escape_markdown` moved to `textutil.py` so the rule
  engine no longer imports the export layer.
- Removed obsolete audit sample files and dead `auctelis delta` / `baseline save`
  / `validate claim` documentation; fixed the Docker Compose duplicate service.

### Removed

- `approved_findings[]` population and the `--accept-gated` acceptance note
  (`--accept-gated` remains an explicit human override that records nothing).
- Default SARIF upload in the Action (`upload-sarif` defaults to `false`).
- Eval rows/configs without a fixture; the external repo manifest is empty until
  a real pilot exists.
- Legacy `sigstore-release.yml` duplicate workflow and unused Action `profile`
  input.

## [0.3.4] — 2026-11-13

### Fixed

- Wheel / clean-venv start: product CLI no longer imports maintainer
  `build` / `deps` / `corpus` / `lint` at startup (`packaging` stays
  `[dependency-groups].dev`). `auctelis --version` works from the built wheel.
- `release.yml` now `needs: [validate, wheel-smoke]` and mirrors
  `pip-audit` + clean-venv smoke (including `--version`) before attaching assets.

### Added

- Authority Watch front door: `auctelis hook install` (session-start delta +
  PreToolUse lock-enforcing hook templates under `~/.auctelis/hooks`).
- Lock-enforcing PreToolUse: refuses MCP server names absent from
  `AUTHORITY.lock`, and continues to block authority-file edits.
- Eval scaffold under `eval/configs/` for labeled FP/FN work.

### Changed

- North star: host-first Authority Watch; PR gate is the team upsell.
- Action quickstart is **lockless-first** (`locked` default `false`);
  `strict-ruleset` default **`true`** (UNVERIFIED protection fails growth).
- Gate CLI `--strict-ruleset` defaults on; use `--no-strict-ruleset` for
  best-effort.
- One public verdict vocabulary: `PASS` / `GROWTH` / `NEEDS_REVIEW` /
  `BASELINE_ADOPTED`. Scan short summary leads with `Authority delta:`;
  legacy `DECISION: BLOCK` is annotations-only.
- PR comment: less path escaping, deduped destinations, skip representation
  noise, one Risk line per addition tagged `LITERAL_CONFIG` /
  `INFERRED_HINT`, coverage % removed from comment body, `explain` follow-up.
- `approvals[]` / `approved_findings[]` remain empty decorative fields
  (not gate inputs); schema docs mark them legacy.
- Product / package version **0.3.4**. Pins in README / INSTALL / Action
  templates repointed to `@v0.3.4`.

### Removed (kill list / demoted)

- Scanner `BLOCK` / SARIF as a public gate language (kept as annotations +
  optional export).
- `auctelis-dev run` / `snapshot` / `artifact-vet` demoted off the product
  front door (still on `auctelis-dev` only).

### Fixed (cleanup / honesty)

- Docs and `ci init` messaging now match lockless-first (`locked: false`) and
  `strict-ruleset` default on; no longer claim the generated workflow is already
  `locked: true`.
- Product strings point at `auctelis-dev snapshot` / `run` (not the product CLI).
- PreToolUse lock hook fail-closed when the lock has zero MCP allowlist entries.
- Lock diff destination lines dedupe URL host vs bare host.

## [0.3.3] — 2026-11-13

### Added

- Gate `--strict-ruleset` / Action `strict-ruleset`: fail growth when ruleset
  status is `UNVERIFIED` (default remains best-effort with a prominent warning).
- Explicit adoption ceremony: `BASELINE_ADOPTED` distinct from growth-gate
  `PASS`; Action step summary + `adoption_bootstrap_verdict()` helper.
- Field-level lock diff lines (`capabilities` / destinations / env / pin /
  approval old → new) for PR Authority Diff comments.
- Pilot kit: `docs/pilots/` tracker, `eval/pilot-metrics.csv`, GitHub pilot
  issue template; EVALUATION-PROTOCOL / ROADMAP wired to the kill criterion.

### Changed

- Inventory skips all `auctelis-out-*` artifact directories (not only a fixed list).
- Remove unused `AesaPolicy` alias; consolidate home-lock path helper.
- Demo CLI help / PRODUCT command table: doctor-first, demo optional.
- Product / package version **0.3.3**.

### Fixed

- Reconcile `authority-policy.schema.json` with `policy.py` (contract **1.3**):
  `output_dir` / `baseline` / `require_review` / expiring `ignore`; drop unused
  `allow_*` fields and top-level `owners`.
- Docs: INSTALL / CLI / GUARD / GATE / tools README bare-command prose matches
  doctor-or-scan; install pins and version tables → **0.3.3**.
- Release manifest: `open_alias` / `fix_alias` marked disabled; build checks
  reject re-enabling them and catch install/doc/schema drift.
- Gate reports distinguish `PASS / protection verified` vs
  `PASS / protection unverified`.
- Remove stale `auctelis open` residue from rules, vet docs, and issue templates.
- Markdown link checker ignores local `auctelis-out-*` / `.pytest_cache` trees.

## [0.3.2] — 2026-11-13

### Fixed

- Action: adoption bootstrap — `locked=true` with no base-ref lock passes when
  head introduces `AUTHORITY.lock` (still fails when both are missing).
- Docs and skill: remove dead `open` / `init-gate` / `fix` / `delta` aliases;
  align AUTHORITY-LOCK / CLI / PRODUCT with lock-only gate.
- Delete unused `build_approval_record`; stop claiming lock `approvals[]` as a
  gate input.

### Changed

- **Lock-only gate:** auctelis labels GROWTH/REDUCTION and requires CODEOWNERS +
  best-effort ruleset check; removed PR-approval re-implementation
  (`--approved-by`, review pagination, lock `approvals[]` as a gate input).
- Default scan excludes `tests` / `examples` / `docs` / `fixtures` /
  `demo-vulnerable` (opt in with `--include-fixtures`).
- Bare `auctelis` → `doctor` when no repo config, else `scan .`.
- `doctor --since-lock` one-screen host delta; Claude PreToolUse hook is Python JSON.
- Advanced `run` / `snapshot` / `artifact-vet` moved to `auctelis-dev`.
- ROADMAP shrunk to a 10-line north star; `eval/` holdout sample scaffold added.
- `release.yml` validate job runs corpus (mirrors `auctelis-validate.yml`).
- `AUTHORITY_PATH_HINTS` includes workflows, actions, and CODEOWNERS.
- Dogfood `AUTHORITY.lock` re-sealed without fixture/example noise.
- Product / package version **0.3.2**.

### Notes

- Prior GitHub Releases `v0.3.0` / `v0.3.1` shipped with empty asset lists;
  this tag should attach wheel, sdist, cosign bundles, and SBOM via `release.yml`.

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
- Prefer `AuctelisPolicy` type name in the scan path (`AesaPolicy` alias retained).
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
- Branch-protection / ruleset guidance in `AUCTELIS-GATE.md`.
- Rebrand debris in the Action PATH check.
- Preflight no longer depends on removed `audit` module; dispatch helpers restored after shrink.

## [0.2.0] — 2026-11-10

### Added

- `auctelis gate --base-lock` — fail on unapproved addition/expansion until a
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
- Policy type preferred name is `AuctelisPolicy` (`AesaPolicy` kept as alias).

### Fixed

- Policy YAML parser accepts `ignore: []`, flow lists, and trailing `#` comments
  (day-one `ci init` → `scan --policy` no longer crashes).
- GitHub Action compares head against the **base-ref** `AUTHORITY.lock` via
  `--base-lock` (real authority delta, not head-vs-own-lock).
- PR comment keeps full risk-delta evidence, sorts by severity, shows destination
  hosts, and labels advisory decisions as `ADVISORY (would BLOCK)`.
- `auctelis lock` refuses HIGH/CRITICAL gated trees without `--accept-gated`.
- `auctelis ci init` requires `--owner` (no `@YOUR_TEAM` placeholder).
- Workflow files are no longer double-registered as Automation + CI Workflow.
- Lock seal excludes volatile `repository` path / `audited_commit` (stable hash).
- `auctelis demo` leads with `+/-` lock lines and always exits 0.
- `auctelis doctor` stages `~/.claude` so settings/hooks resolve; parses
  `.claude.json` as MCP config.

## [1.0.0] — 2026-11-09

### Added

- Initial **auctelis 1.0.0** release as a clean product line:
  authority lockfile + PR security gate for AI agents.
- Public CLI: `auctelis` / `auctelis-dev` (package name `auctelis`).
- Core path: `demo` → `doctor` → `vet` → `scan` → `lock` → `ci`.
- `AUTHORITY.lock`, Authority Diff PR comments, GitHub Action gate,
  deterministic rules, and optional coding-agent skill.

### Changed

- Rebranded from the prior AESA / `aesa-tools` product line.
- Policy file: `.auctelis.yml` · artifacts: `auctelis-out/` ·
  Action: `auctelis-gate` · rules: `AUCTELIS-RULE-NNN`.
- All first-party version surfaces reset to **1.0.0**.
