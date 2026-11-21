# Changelog

All notable changes to **Auctelis** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

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
