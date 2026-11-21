# Changelog

All notable changes to **Auctelis** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

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
