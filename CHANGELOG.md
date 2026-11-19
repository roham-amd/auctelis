# Changelog

All notable changes to **Auctelis** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

## [0.14.0] — 2026-11-19

### Added
- **AUCT-007 (Complete Reach Report):** `reach_snapshot` now includes uncapped
  `records` alongside capped `top` / `top_cards`. `check --report` Tier-2 tables
  and `--baseline` diffs use the full inventory (legacy JSON still falls back to
  `top`).
- **AUCT-007 (Lockless `diff --base`):** When the base ref has no
  `AUTHORITY.lock`, extract tree-truth authority via a temporary detached
  worktree (`baseline_state=tree`) and emit a real base→head Authority Diff.
- **AUCT-008 (Scan limits):** Default walk caps raised to 50 000 files /
  depth 16; count only kept files; override with `--max-files` or
  `AUCTELIS_MAX_FILES` / `AUCTELIS_MAX_DEPTH`.

### Fixed
- **AUCT-008 (Honest install PR):** First-run comments stay `PASS` / Watching
  when the only growth is `.github/workflows/auctelis*.yml`; install PRs that
  also add MCP/hook growth keep `NEEDS_REVIEW` with delta cards. The Action no
  longer overwrites a material `pr-comment.md` with a Watching-only file.

### Changed
- **AUCT-009 (Lean Action):** Removed deprecated Action inputs (`baseline`,
  `baseline-inventory`, `fail-on`, `no-policy`, `upload-sarif`, `annotate`) and
  all `auctelis-dev` / research / SARIF steps from `auctelis-gate`. Templates
  drop `annotate: false`.
- **AUCT-009 (Lock write):** New `AUTHORITY.lock` files omit empty `approvals` /
  `approved_findings` (legacy locks with those fields still load). Dropped
  deprecated `lock --approval`.
- Build guards `docs/CLI-REFERENCE.md` package/product version against
  `VERSION`.

## [0.13.3] — 2026-11-19

### Fixed
- Release workflow installs workspace member `auctelis-dev` via `uv sync --all-packages` before metadata verify / SBOM (unblocked GitHub Release assets).

## [0.13.2] — 2026-11-19

### Fixed
- Authority content digests normalize CR/LF to LF so Windows working trees seal the same `AUTHORITY.lock` digests as Linux CI (dogfood representation drift).
- Inventory walk skips `pytest-of-*` / `auctelis-pytest` basetemp trees so local pytest leftovers cannot pollute dogfood `check` / `lock`.

## [0.13.1] — 2026-11-19

### Fixed
- Resealed `AUTHORITY.lock` after 0.13.0 workflow edits so dogfood `check` / `lock --check` stay green on CI.

## [0.13.0] — 2026-11-19

### Distribution
- **AUCT-004 (Install truth):** Product wheel ships only the `auctelis` console
  script; maintainer `auctelis-dev` moved to source-only workspace member
  `tools/dev`. Release refuses tag ≠ `v$(VERSION)`. Publish workflow asserts
  PyPI HTTP 200 for the released version. `pypi_live` in
  `canonical/release-manifest.json` drives install-doc guards (git-tag primary
  while false). Docs no longer claim PyPI is done or defer with "once published".

### Added
- **AUCT-005 (Reach Report):** `auctelis check --report DIR` writes
  `reach-report.html` / `.md` / `.json` plus `authority-sbom.json`, with an
  honesty panel (coverage, NOT PARSED, truncation, declared-only). Optional
  `--baseline PATH` diffs against a prior report JSON.
- **Org reusable workflow:** `docs/auctelis-org-reusable.yml` for
  `workflow_call` from an org `.github` repo.

### Fixed
- **AUCT-006 (Enforce integrity):** Deleting `AUTHORITY.lock` under enforce
  while the base lock had records is drift (`NEEDS_REVIEW`), not a silent PASS.
  Legacy Action inputs (`baseline`, `baseline-inventory`, …) warn and no longer
  skip auth-diff. `strict-ruleset` defaults on when `locked=true`. Install PRs
  always get a Watching proof comment (CLI always writes
  `comment-first-run.md`; Action prefers it when the workflow file is new).
  Trusted hosts never lower new MCP / Hook / Host Settings. Walk truncation is
  surfaced and fails enforce like unparsed configs.

### Changed
- Kill list: circular "PyPI waits for five pilots" rule removed. Positioning
  centers the shareable Agent Reach Report; gate remains the second surface.
- Cleanup: shared truncation/coverage honesty helpers in `inventory/coverage.py`;
  Action research coverage/SARIF notes gated on `annotate=true`; base-ref step
  renamed to tree-truth lock extraction; CONTRIBUTING documents `tools/dev`
  workspace + `check --report`.

## [0.12.2] — 2026-11-19

### Fixed
- **AUCT-001 (Real-Repo Signal & TOML Scope):** Removed `CI Workflow`,
  `Workflow`, and `Plugin` tier-2 `TYPE_DEFAULT` injections from
  `capabilities.py`, added `execute_commands` to tier-2 reach in
  `reach_tiers.py`, capped non-agent CI workflows below tier 2, and scoped
  `config.toml` discovery in `toml_config.py` (and `hosts.py`) to agent
  directories (`.codex/`, `.cursor/`, `.claude/`, `.gemini/`, `.opencode/`).
- **AUCT-002 (Quiet-PR Silence & `BASELINE_ADOPTED`):** Restricted
  `comment-first-run.md` to PRs that add `.github/workflows/auctelis*.yml`
  so ordinary quiet PRs post zero comments; added `base_lock_committed` output
  and head `auctelis lock --check` verification in `action.yml` so first-time
  `--enforce` adoption PRs reach `BASELINE_ADOPTED`.
- **AUCT-003 (Working First-Run Install & Fast Lockless Action):** Updated
  `README.md`, `docs/INSTALL.md`, and `build.py` to lead with the working
  `uvx --from git+…` one-liner until PyPI is published; removed
  `fetch-depth: 0` from templates and example workflows; added shallow
  `--depth=1` base fetch and a watched-path short-circuit before `setup-uv` in
  `action.yml`; documented `auctelis-dev` as a source-only entry in
  `tools/pyproject.toml`.
- **Action & Gate Hardening:** Fixed shallow-clone `...HEAD` diff crash and
  head-CODEOWNERS trust gap in `action.yml`'s `.auctelis.yml` edit check;
  fixed CODEOWNERS `/**` / `/**/*` directory boundary prefix matching in
  `gate.py`.

### Changed
- Consolidated duplicated static-analysis hint regexes and markers into
  `inventory/hints.py`, unified JSON and TOML MCP server normalization via
  `build_mcp_server_entry` in `inventory/adapters/mcp.py`, aligned Claude
  `UserPromptSubmit` / `printenv` hook hints, sorted `iter_repo_files` walk
  order while skipping local cache dirs, and deduplicated `FAIL_CLOSED` report
  building in `gate.py`.

## [0.12.1] — 2026-11-18

### Added
- PyPI one-line install: `uvx auctelis check` is now the documented first run,
  with the git tag and signed wheel kept under a fallback heading. The build
  fails on any stale `git+…@vX` / `auctelis==X` install pin
  (`check_public_install_versions`), so a release bump cannot leave the docs
  behind.
- First-run proof: the first quiet (`NONE`) PR after install posts one
  "Watching: N reach surfaces …" comment. It is emitted only when no sticky
  comment exists yet, so a healthy install is no longer indistinguishable from a
  broken one. Later no-change PRs stay silent.
- `gate` reports now carry a head reach snapshot (`reach`) used by the first-run
  comment.

### Fixed
- Prose inference is capped at the comment tier. A record whose only evidence is
  `INFERRED_HINT` no longer reaches tier 2 from a word like "secrets"; tier 2
  requires a literal signal (declared `env_keys` or a launcher). Cards say
  `tier 1 (inferred hint)` instead of naming a capability the config never
  declared. Matches [`docs/REACH.md`](docs/REACH.md).
- Trusted destinations no longer lower a record that declares a launcher. Host
  trust covers network-only reach; a trusted host must not hide the executable
  an MCP server starts. URL-only registrations are still lowered to the comment
  tier.
- `auctelis-dev run` works again: its positional argument no longer overwrites
  the subcommand name, so `run -- <cmd>` executes instead of exiting 2.
- Invalid JSON / unreadable report or graph files now fail with a clear message
  instead of a traceback (`validate report`, `validate graph`, `export sarif`).
- Stale 0.9.1 pins in the CLI reference, security-rules header, and explainer
  skill; docs index now lists six public pages (everything else is documented
  as maintainer depth); README first run shows two surfaces and the correct
  diff-template path.

### Changed
- CLI architecture: `cli/dispatch.py` now holds only the product command
  handlers (check/lock/init/status/gate/diff/trust/why/demo/ci); maintainer and
  research handlers live in `cli/dev_commands.py`, so the product surface stays
  small and the research boundary is explicit.
- Reach tiering shares one `_literal_signal` helper instead of three copies of
  the same condition; `gate` imports its tier/comment dependencies at module
  scope.
- Release 0.12.1 pins across templates, consumer example, pilot tracker, and
  install docs.
- Test suite: new coverage for the maintainer CLI split, reach-tier edges,
  `require_review` class matching, report/graph validation errors, versioning
  fallbacks, gate fail-closed paths, and the install-docs build guard.

## [0.12.0] — 2026-11-17

### Added
- `auctelis check` is now a ranked reach report: `Reach:` tier counts and the
  top five cards even when `AUTHORITY.lock` matches; `--top N` and `--json`
  expose the ranking; `--pins` is the MCP pin doctor.
- `auctelis trust <host>` manages `.auctelis/trusted-hosts` (`--list`,
  `--remove`, `--init`). Trusted destinations lower network-only reach to the
  comment tier; secrets/execute/approvals/unattended/env keys still fail.
- Cards name secret **names** (`env: API_TOKEN`) and the reach tier reason
  (`tier 2 (secrets)`); added cards no longer hide env reach.
- MCP pin doctor: `check --pins` lists unpinned npx/uvx/docker launchers with a
  concrete pin suggestion.
- `status --require-protection` for CI that must fail on an UNVERIFIED ruleset.

### Fixed
- `diff --base` works on a repo that has never sealed `AUTHORITY.lock`:
  the ref is resolved first, a missing lock is `BASELINE_NEEDED` (exit 0, no
  files written), and only an invalid ref fails closed. JSON carries
  `baseline_state`; real base-lock diffs no longer say "absolute head scan".
- Comment-only growth is `NEEDS_REVIEW`, not `PASS`. The Action still exits 0,
  but reviewers no longer see a false approval on a new MCP/token.
- A no-change PR no longer posts an Authority Diff by default
  (`comment-on-none: false`; an existing sticky is updated once to "no
  change"). `comment-on-none: true` or `--comment-policy always` restores it.
- `init` in comment-only mode no longer prints an enforce ruleset checklist;
  `status --check` on a correct enforce install reports "verify in GitHub"
  instead of failing offline.

### Changed (maintenance)
- Removed unused card/summary helpers and a retired finding-explanation renderer.
- Centralized the empty-lock shape and seal-hash exclusions so `check`,
  `diff --base`, and `lock` cannot drift.
- GitHub/PyPI URLs are validated as http(s) before `urlopen`; git discovery uses
  `shutil.which` instead of relying on a partial executable path.
- Trusted destinations reject TLD-only and wildcard entries so a trust file
  cannot allowlist an entire suffix.
- `auctelis-dev build` now fails when wheel-only embedded version fallbacks drift
  from `canonical/versions.json`.
- Docs, templates, Action examples, and version tables aligned to 0.12.0.

## [0.11.0] — 2026-11-17

### Fixed
- Action no longer warns that `locked=false` is “unchecked” — that is the
  supported comment-only default.
- `install-tools-from: path` no longer requires `auctelis-dev` unless
  `annotate: true`.
- Plain CI workflows are not automatic secret reach; Plugin / Subagent
  additions no longer auto-fail without launcher / env / agent evidence.
- Inferred doc-link host expansions stay comment-tier (visible, non-fail).
- `download_and_execute` hints require a real pipe-to-shell pattern.
- `status --check` treats comment-only installs as ready (enforce still must
  be armed when `locked=true`).

### Changed
- Action product path installs with `uv sync --no-editable` (research omitted);
  `annotate: true` keeps editable sync for `auctelis_research`.
- Gate accepts `--comment-only` (Action passes it when `locked=false`).
- PR comment shows `mode comment-only|enforce` and caps cards at five.
- Docs / templates / install pins → `@v0.11.0`; AUTHORITY-LOCK documents
  reach-tier `material_authority_change`.
- Build prefers the current-version wheel when checking research omission.
- Wheel-smoke asserts `auctelis_research` is not importable from the product
  wheel (`python -P` so the tools/ checkout is not on ``sys.path``).

### Compatibility
- Existing `locked: "true"` workflows keep enforce behavior.
- Research scanner remains source-checkout / `auctelis-dev` only.

## [0.10.0] — 2026-11-17

### Fixed
- `init` CODEOWNERS no longer strips leading dots via `str.lstrip("./")`
  (`.vscode/…`, `.cursor/…` stay covered).
- TOML MCP configs use stdlib `tomllib` (Codex `args = ["-y", "pkg"]` seals).
- `NEEDS_REVIEW` errors no longer keep a leftover `PASS / …` label.
- Dogfood `AUTHORITY.lock` resealed; `release.yml` mirrors validate dogfood +
  Windows/macOS matrix.
- `init` rolls back newly written setup files when the lock seal refuses.
- `status` reads `strict-ruleset: true|false` from the workflow Action input.

### Changed
- `init` defaults to **comment-only** (advisory); pass `--enforce` for locked
  + strict ruleset.
- Reach tiers (0 silent / 1 comment / 2 fail): inferred doc-link network no
  longer pages CODEOWNERS the same as execute/secrets/new MCP.
- Research scanner moved to `auctelis_research/` and **omitted from the product
  wheel** (`rules`, `scan`, annotate, broker, snapshot, corpus, graph, …).
- Lockless Action path: `templates/auctelis-diff.yml`; Action defaults
  `locked=false` / `strict-ruleset=false` and still posts the tree-truth comment.
- Pilot slots + `eval/pilot-metrics.csv` + `docs/pilots/RECRUITMENT.md` ready
  (PyPI publish still deferred until outside pilots retain).
- First-user path leads with `diff --base` / lockless workflow before enforce.
- Docs/Action/install pins updated to `@v0.10.0`.

### Compatibility
- Existing workflows that set `locked: "true"` keep enforce behavior.
- `auctelis-dev scan` requires a source checkout (not available from the wheel).

## [0.9.1] — 2026-11-17

### Security
- **Material-reach gate:** body/script-digest-only edits stay visible on the
  Authority Diff comment but no longer fail the required check. New hosts,
  launchers, env keys, pin/approval growth, lock↔tree drift, and unparsed
  configs still fail closed.

### Changed
- Action posts the sticky PR comment from the **gate lock delta** on every PR
  (`annotate: false` default). Research `auctelis-dev scan` / annotate run only
  when `annotate: true`.
- `status --check` exits nonzero when `strict-ruleset` is on and ruleset
  protection is `UNVERIFIED` or `MISSING`.
- Instruction/skill `script_digest` classified as representation (cards still
  say "body changed"); prose-derived destination growth remains material.
- Docs/Action defaults and install pins updated to `@v0.9.1`.
- Validate matrix covers tree-truth / strategic-review / trust-reset suites.

### Fixed
- GUARD-SCAN Action input table matched live defaults (`locked=true`,
  `annotate=false`; comment is gate-owned).

## [0.9.0] — 2026-11-16

### Security
- **Tree-truth gate:** head authority is always derived from the working tree.
  A committed `AUTHORITY.lock` is drift-checked only — never trusted as head
  (fixes the growth-without-touching-lock bypass).
- Gate Action extracts base authority from the base worktree and runs
  `lock --check`; dogfood CI targets `$GITHUB_WORKSPACE` explicitly.

### Added
- Prose host extraction for skills, instructions, slash commands, and hooks
  (`curl|sh` / `wget|bash` → destinations as `INFERRED_HINT`).
- `init` merges CODEOWNERS for discovered authority paths and common globs.
- Gate flags uncovered authority paths on growth deltas.
- Adversarial tree-truth replay tests (`tests/test_tree_truth_weeks.py`).

### Changed
- Instruction / skill body digests participate in authority identity
  (`script_digest`); cards say "body changed" instead of "script_digest changed".
- Diff/check/gate agree on body/representation drift (`NEEDS_REVIEW`).
- README leads with the working git-tag install; verdicts list includes
  `FAIL_CLOSED`.
- Docs/Action defaults align to tree-truth: `init` preferred, research
  `annotate` defaults off, consumer pin `@v0.9.0`.

### Removed
- Docker / compose install story.
- Decorative lock fields `approvals[]`, `approved_findings[]`, and legacy
  `mcp_servers` map (no longer emitted).
- Stale `hook_status_week4` pilot-metrics column.
- Redundant `skills/cursor` prompts (auditor skill remains).

## [0.8.2] — 2026-11-15

### Fixed

- **No `fail_on` promotion** — `mode: enforce` + `fail_on: never` stays never
  (lock-only contract; research findings no longer become a de facto gate).
- **Action inventory-only** — required check fails on gate only; research scan
  is `continue-on-error` / advisory.
- **Fail closed on unresolved base ref** — not silent `BASELINE_ADOPTED`.
- **Adoption requires CODEOWNERS** coverage for `AUTHORITY.lock`.
- **`check` / `lock` refuse unparsed** agent configs (no false-green 0-record seals).
- **`evidence_strength` / `capability_origin`** survive lock normalize → PR cards
  keep `LITERAL_CONFIG`; CI type defaults stay `TYPE_DEFAULT`.
- **`init` CODEOWNERS** — merge into root/docs/`.github` without shadowing; `--force`
  never wipes; reports actual workflow locked/mode.
- Instruction / slash-command type defaults include `modify_agent_instructions`.

### Added

- **`auctelis status --check`** — nonzero when the gate is not armed.
- Protection-path CODEOWNERS coverage (lock, policy, workflows, actions, CODEOWNERS)
  when the gate workflow/action is installed.
- Compact PR reach table (up to 10 cards; named overflow).
- Dogfood validate step: `auctelis check .` + `lock --check .`.
- Trust-reset tests (`tests/test_trust_reset_30d.py`).

### Changed

- Generated Action uses **bundled tools** (no consumer `pip install`).
- Demo is lock-only (no findings-first walkthrough).
- Policy docs / example default to `fail_on: never`.
- Eval fixture score **22 TP / 0 FP / 0 FN / 3 TN** (cfg-024 TP).
- Install docs prefer `uvx auctelis` + signed wheel / cosign.

## [0.8.1] — 2026-11-15

### Fixed

- **Consumer Action pin** — `init` / `ci init --apply` pin the Action to the
  auctelis **release tag** (`v0.8.1`), never consumer-repo HEAD
  (which returned GitHub 422 outside the dogfood repo).
- **Empty-baseline growth** — a 0-record base lock + head authority is `GROWTH`
  needing CODEOWNERS, not permanent `FAIL_CLOSED`.
- **`strict-ruleset: false`** — Action now passes `--no-strict-ruleset` (CLI
  default is already true; omitting the flag was a no-op).
- **`ci init` exit** — ruleset probe failures are warnings; exit 0 after writes.
- **Post-init relock** — generated workflow/policy changes refresh `AUTHORITY.lock`.

### Added

- **`auctelis init --owner @team`** — one-command setup (preferred front door).
- **`auctelis status`** — lock / workflow / CODEOWNERS / protection summary.
- Consumer-repo + empty-baseline recovery tests (`tests/test_recovery_081.py`).

### Changed

- Product `check` / `lock` / `gate` / `diff` use **inventory-only** scans; the
  22-rule research scanner stays on `auctelis-dev scan` and is not a gate input.
- Evidence strength derived from declared-config kind + path (not adapter maturity).
- `"Claude slash command"` sealed in authority kinds (cfg-024).
- `MCP Server Implementation` source files excluded from the lock by default.
- PR cards risk-ranked; overflow can summarize bypass/execute/secrets.
- `check` inventory line includes `other` / `host`; "Gated findings" → advisory.

## [0.8.0] — 2026-11-15

### Added

- **`auctelis diff --base <ref>`** — local PR Authority Diff simulator (same
  comment dialect as the Action).
- **`ci init --apply`** — merge `AUTHORITY.lock` into existing CODEOWNERS, pin
  the Action to a commit SHA when resolvable, and verify ruleset protection
  (prints exact GitHub remediation when unverified).
- **`evidence_strength`** / `capability_origin` / `parser_version` on lock
  records; cards and `why` render the real value (no hardcoded `LITERAL_CONFIG`).
- **`gate --trust-head-codeowners`** — explicit unsafe flag; growth without a
  base-ref CODEOWNERS copy fails closed otherwise (CI passes `--codeowners`).
- Effective-rules probe via `/repos/{repo}/rules/branches/{branch}`.
- Adoption sticky comment overwrites scan `PASS` with **`BASELINE_ADOPTED`**.
- `check` always prints family coverage + gated findings; match is not a clearance.
- `lock_hash` verified on load.

### Changed

- One vocabulary: meaningful lock drift is `NEEDS_REVIEW` (`AUTHORITY_CHANGED`
  retired).
- Host/changed/removed cards always include `@ path` + evidence tag.
- Generated consumer workflow no longer requests `security-events: write`
  (no SARIF upload).
- Build guard covers `SECURITY.md`, `CONTRIBUTING.md`, `AUTHORITY-LOCK.md`.
- Docs truth reset: no Authority Watch front door; `gate --base-lock base.lock`.
- GitHub Action annotation steps use `auctelis-dev scan` / `annotate`.
- Eval suite expanded to **25 labeled fixtures** (`eval/configs/cfg-001`…
  `cfg-025`); score with `python eval/score_configs.py`
  (21 TP / 0 FP / 1 FN / 3 TN — fixture regression, not external precision).

### Removed

- Host stack CLIs and modules: `watch`, `allow`, `hook`, `doctor`, `ledger`,
  `host_scan`, Cursor/Claude tripwire plugins and hook templates.
- Public product CLIs: `vet`, `harden`, `explain` (and product `scan` /
  `annotate` — moved to `auctelis-dev` only).

### Security

- Disabled rulesets are not treated as protection.
- Classic branch-protection 403 documented as UNVERIFIED (Administration scope).

## [0.7.0] — 2026-11-15

### Added

- **`auctelis check`** — repo-only authority vs `AUTHORITY.lock` (product front
  door). JSON schema `authority-diff/1` via `--json`.
- **Full project discovery in the lock path** — skills (`.claude/skills`,
  `skills/`), instructions (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.clinerules`,
  `.cursor/rules`), subagents, and plugins become sealable records.
- **`ci init --advisory`** — opt out of enforce; default is enforce
  (`locked=true`, `policy.mode: enforce`).
- Authority cards always show `@ path` so PR reviewers can jump to the file.

### Changed

- **North star:** GitHub-native Authority Diff + enforcement gate (not Project
  Trust / host hooks). Positioning: “the authority lockfile and PR review for
  what AI agents can reach.”
- Public path: `check → lock --update → ci init --owner → gate`.
- Bare `auctelis` → `check` (was `watch`).
- Action `locked` default is **true**.
- Stale 0.5.0 docs / dogfood lock bumped.

### Archived (callable, hidden from help)

- `watch` / `allow` / `hook` / `doctor` — host seal, project-allow store, and
  tripwire install remain for compatibility but are not the product path.

### Fixed

- Docs / skills / plugins / CI matrix aligned to the Authority Diff front door
  (no more bare-`watch` as the documented default).
- `dispatch` imports host staging from `host_scan` (not via `doctor` re-exports).
- Build guard rejects stale “bare auctelis runs watch” copy in public docs.

### Compatibility

- Existing locks remain valid; regenerate after upgrading to pick up new
  instruction/skill surfaces.
- `scan --locked` still works for the hidden annotation layer.
- Git-tag install remains the supported path until PyPI returns 200.
- Archived `watch` / `allow` / `hook` / `doctor` remain callable.

## [0.6.0] — 2026-11-15

### Added

- **Consent integrity:** first-class permission-posture cards
  (`bypassPermissions`, `+allow Bash(*)`); Host Settings always on screen;
  `watch --seal --accept <digest>` refuses seal unless the screen digest matches.
- **curl|sh host extract:** destination host from `curl`/`wget` pipelines lands
  in destinations / cards (`→ evil.example`).
- **Project Trust:** project-level discovery (`.mcp.json`, `.claude/settings.json`,
  `.cursor/mcp.json`, commands/hooks) + `auctelis allow --accept <digest>` store;
  watch surfaces project-allow status.
- **Hook hardening:** absolute interpreter paths at install; per-host heartbeats;
  `hook status --probe` (exit 1 on fail); malformed hook stdin fails closed.
- **Distribution:** `plugins/claude/` and `plugins/cursor/` bundles.

### Changed

- Public path: `watch → --seal --accept → allow → --arm → why → hook status`.
- Roadmap north-star is Project Trust (direnv allow for agent authority).
- Lock schema records may include `permission_allows`.
- First-run screen shows every sealable record (no silent truncation).

### Compatibility

- Existing `AUTHORITY.lock` files without `permission_allows` remain valid.
- `--seal` without `--accept` now fails closed (exit 2) — intentional consent fix.
- Hidden scanner / gate / Docker remain callable; not required for install.

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
