## [Unreleased]

## [0.1.6] — 2026-11-22

### Added

- **AUCT-048:** `auctelis rollout REPORT --status` is a read-only funnel ledger
  (GET only). Classifies each target as `open` / `merged` / `closed_unmerged` /
  `never_opened` / `watching_on_default` / `unknown`, including already-watching
  repos. Emits a table, `--json`, or `--csv` (columns ⊂ `eval/pilot-metrics.csv`).
  Mutually exclusive with `--apply`; allowed under `AUCTELIS_AGENT=1`.
- **AUCT-049:** Fleet / `--github` audits accept `--baseline` and print
  **Changed since last audit** (MD/HTML/summary) after Summary. JSON gains
  `baseline_diff` only when a baseline is given. Schema mismatches exit 2.
  [`docs/auctelis-org-audit.yml`](docs/auctelis-org-audit.yml) fetches the prior
  run's `auctelis-org-report` artifact (`actions: read`) and passes `--baseline`
  when present; first runs say `no baseline`. Cron stays opt-in.
- **AUCT-050:** `check --pins --resolve-pins` / `check --report --resolve-pins`
  looks up exact npm/PyPI latest versions (5s timeout; Docker stays a
  placeholder). Additive `resolved_pin` / `resolved_at` /
  `resolved_config_snippet` fields; labeled trust-on-first-use. `rollout` prefers
  a resolved snippet when present and adds no network of its own. Live PR gate
  stays offline.

### Changed

- Roadmap Next row no longer implies PyPI claim is the immediate next step;
  PRODUCT.md drops Marketplace pitch wording for the root Action.
- Validate / Release OS matrices now cover `test_rollout_status`,
  `test_pin_resolve`, and `test_fleet_baseline`.

## [0.1.5] — 2026-11-21

### Added

- **AUCT-045:** `auctelis rollout` Watch PRs embed per-repo reach findings and a
  literal `Pin fix`, support `--repo` / `--min-tier` pilot filters, and inherit
  `org_reusable` from `reach-report.json`. Fleet Summary CTAs include
  `--org-reusable` when set.
- **AUCT-047:** Copy-paste [`docs/auctelis-org-audit.yml`](docs/auctelis-org-audit.yml)
  runs `check --github` on GitHub Actions (`workflow_dispatch` / optional weekly),
  posts the Reach Report to Job Summary, dry-runs `rollout`, and uploads
  `reach-report.{html,md,json}` — zero local `uv`/`git` under `pypi_live=false`.

### Fixed

- **AUCT-046:** Live PR / first-run comments preserve MCP launcher `args` in
  `Pin fix` snippets (`gate`, `diff --base`, `demo`). Clean install Watching
  comments surface one `Pin fix` (≤12 lines) and the zero-reach footer uses the
  git-tag CLI prefix while PyPI is deferred.

### Changed

- Removed unused `select_unwatched_tier2` wrapper and `_attach_launcher_args`
  alias after the AUCT-045/046 call-site migration.

`pypi_live` stays false. The PyPI name is still unclaimed, so install docs
keep the git-tag pin. Cutover order remains claim → bump+flip PR → publish →
live probe → tag.

## [0.1.4] — 2026-11-21

### Added

- **AUCT-044:** `auctelis rollout REPORT_JSON` opens lockless Watch PRs from a
  Reach Report on Windows, macOS, and Linux. Dry-run is the default; `--apply`
  skips repos that already have an Auctelis workflow or an open
  `auctelis/watch-prs` pull request, and retries the workflow write with the
  existing blob `sha`. `--org-reusable ORG` installs the six-line caller.
  Fleet summaries lead with this command. `rollout-watch-prs.sh` stays as an
  optional Bash fallback. `AUCTELIS_AGENT=1` refuses `--apply`.

### Fixed

- **AUCT-042:** Pilot recruitment now follows claim → bump+flip PR → publish →
  live probe → tag, and the truncated `git+…` install lines are full commands.
  `check` overflow / drift footers and `init --lockless` use the git-tag CLI
  prefix while `pypi_live=false`. The demo agent workflow invokes `claude` in
  command position so `examples/demo-vulnerable` stays tier 2.
- **AUCT-043:** `Pin fix` snippets keep the rest of an MCP `args` list, strip
  floating `@latest` / `:latest` tags before appending a pin, and emit a valid
  `"args"` array for Docker and Podman. Snippets longer than 100 characters
  are still omitted rather than truncated.

`pypi_live` stays false. The PyPI name is still unclaimed, so install docs
keep the git-tag pin. Cutover order remains claim → bump+flip PR → publish →
live probe → tag.

## [0.1.3] — 2026-11-21

### Added

- **AUCT-039:** PyPI cutover order is claim → bump+flip PR → publish → live probe → tag.
  `auctelis-dev build pypi-check` requires the packaged release manifest to match
  canonical (and the built wheel, when one exists). `publish-pypi.yml` polls PyPI
  for up to 10 minutes, then runs `pypi-check --live`. `release.yml` fails a
  Release with fewer than 6 assets. `pypi_live` stays false until the package
  name is claimed.

### Fixed

- **AUCT-040:** PR-comment `Pin fix` is a literal code span. Newlines and
  over-budget snippets are omitted instead of truncated or backslash-escaped.
  The Reach Report uses the same snippet helper.
- **AUCT-041:** Reach reports (Markdown and HTML, single repo and fleet) lead
  with a Summary: tier counts, the top tier-2 findings, and a Pin fix when one
  exists. Honesty and Not-auto-inspected sit under Coverage and limits. The
  JSON document is unchanged.

### Changed

- Removed unused `_is_unpinned_mcp` alias; document Reach Report Summary-first
  layout in `docs/REACH.md` and `docs/CLI-REFERENCE.md`.

## [0.1.2] — 2026-11-21

### Added

- **AUCT-036:** Copy-pasteable first-run CLI CTAs when `pypi_live=false` (full
  `uvx --from "git+…#subdirectory=tools"` prefix in `check` / `demo`); Action
  version example matches release; `auctelis-dev build pypi-check --live`
  probes PyPI HTTP status without flipping cutover.
- **AUCT-037:** Agent-only CI precision — plain non-agent workflows (including
  `secrets.*` and bare `pull_request_target`) score tier 0 and stay quiet under
  lockless PR Watch; agent-step CI remains tier 2.
- **AUCT-038:** PR comments include one escaped `Pin fix:` snippet for unpinned
  MCP growth (`package_stem` fallback); `check --report --org-reusable ORG`
  emits org-reusable `rollout-watch-prs.sh` (checks `auctelis.yml` and
  `auctelis-gate.yml`).

## [0.1.1] — 2026-11-21

### Added

- **AUCT-033:** `auctelis-dev build all` fails on dogfood `AUTHORITY.lock` drift
  before tagging; version bump to **0.1.1** (PyPI cutover still `pypi_live=false`
  until Trusted Publishing serves HTTP 200).
- **AUCT-034:** Calm lock mode — plain-CI / prose `representation` digest drift
  is advisory by default on `check` / `lock --check` / gate lock↔tree freshness;
  opt into byte-strict with `--strict-digests`. Hook body edits still fail closed;
  PR comments still show `body changed`.
- **AUCT-035:** Fleet reports emit executable `rollout-watch-prs.sh` (dry-run
  `APPLY=0` by default) and `watch_pr_url` prefills the commit message.

### Fixed

- Org reusable workflow `actions/checkout` pin aligned with dogfood gate.
- Example Authority Diff cards no longer inline `publisher NOT VERIFIED`
  (footer-only caveat).
- CI / release dogfood lock freshness uses `--strict-digests` so plain
  representation churn cannot green-light a broken ship (AUCT-033/034).
- Shared calm-lock advisory string (`STRICT_DIGEST_ADVISORY`).

## [0.1.0] — 2026-11-21

### Added

- Initial **auctelis 0.1.0** release: authority lockfile and PR review for what
  AI agents can reach.
- Public CLI: `auctelis` / `auctelis-dev` (package name `auctelis`).
- Core path: `check` → `init` / `init --lockless` → `lock` → `gate` / `diff`.
- `AUTHORITY.lock`, ranked Reach Report (`check --report`), GitHub Action gate,
  zero-clone `check --github`, and optional coding-agent skill.
- All first-party version surfaces set to **0.1.0**.
