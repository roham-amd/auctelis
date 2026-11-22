# auctelis CLI reference

Primary command: **`auctelis`**.
Maintainer entry: **`auctelis-dev`** (build / lint / corpus / deps / validate / …).

Package `auctelis` **0.1.9** · product **0.1.9** · rule pack **1.6** (001–022).

Product contract / command tiers: [`PRODUCT.md`](PRODUCT.md) ·
reach: [`REACH.md`](REACH.md) ·
lock semantics: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) ·
roadmap: [`ROADMAP.md`](ROADMAP.md).

Install: [`INSTALL.md`](INSTALL.md).

**Default:** bare `auctelis` runs `check` (repo authority vs `AUTHORITY.lock`).

---

## Product command overview

| Tier | Command | Purpose |
| --- | --- | --- |
| Core | `init --lockless` | One-file comment-only PR Watch (no owner, lock, policy, or CODEOWNERS) |
| Core | `init --owner team` | Full setup (policy + workflow + CODEOWNERS + lock) |
| Core | `check [PATH ...] [--top N] [--pins] [--resolve-pins] [--report DIR] [--baseline PATH] [--max-files N] [--github TARGET …] [--max-repos N] [--include-forks] [--strict-digests] [--org-reusable ORG]` | Ranked reach report vs `AUTHORITY.lock` (front door); `--github` zero-clone org/repo audit; multi-path / multi-repo = fleet report; `--baseline` diffs prior report (fleet/`--github` too); `--resolve-pins` opt-in npm/PyPI lookup; `--org-reusable` with `--report` records the org caller for `rollout` |
| Core | `rollout REPORT_JSON [--apply \| --status] [--max-prs N] [--org-reusable ORG] [--show-body] [--pin-sha] [--action-sha SHA] [--json] [--csv]` | Open lockless Watch PRs for unwatched tier-2 repos (dry-run unless `--apply`); `--status` read-only funnel ledger; `--show-body` previews the PR; `--pin-sha` / `--action-sha` pin the Action to a commit SHA |
| Core | `trust <host>` | Trusted destinations for network-only reach |
| Core | `status [--check]` | Lock / workflow / CODEOWNERS / protection summary |
| Core | `lock` | Write / check / update repo `AUTHORITY.lock` |
| Core | `gate --base-lock base.lock` | Tree-truth PR Authority Diff + CODEOWNERS gate |
| Core | `diff --base <ref>` | Local PR Authority Diff simulator |
| Core | `why <name>` | Exact config path / reach fields for one authority record |
| Core | `demo` | Packaged fixture walkthrough |
| Core | `diff lock` | Record-level diff of two `AUTHORITY.lock` files |

Maintainer-only (`auctelis-dev`): `scan`, `annotate`, `build`, `lint`, `deps`,
`corpus`, `hosts`, `validate`, `inventory`, `verify`, `export`, `run`,
`snapshot`, `artifact-vet`. The host stack (`watch` / `allow` / `hook` /
`doctor`) and public `vet` / `harden` / `explain` CLIs were **removed**.

---

## `auctelis check`

```bash
auctelis check [PATH ...] [--lock-file PATH] [--json] [--top N] [--pins]
               [--resolve-pins] [--report DIR] [--baseline PATH] [--max-files N]
               [--github TARGET ...] [--max-repos N] [--include-forks]
               [--strict-digests] [--org-reusable ORG]
```

Inventories agent configs in a repository (MCP, skills, instructions, hooks,
rules, subagents, plugins, CI) and diffs them against the committed
`AUTHORITY.lock`. No host home scan. Prints a ranked reach summary and the top
five cards even when the lock matches (`--top 0` hides cards). `--report` always
lists every tier-2 record (not just the top cards).

- No lock yet → inventory + JSON `BASELINE_NEEDED` (terminal: `Mode: lockless`) and exit 0; unparsed agent configs
  override this to `NEEDS_REVIEW` / `GROWTH` and exit 1
- Lock matches → `LOCKED`, still showing reach counts and top cards
- Lock drifts → cards with `@ path` + `NEEDS_REVIEW`
- `--pins` → unpinned/floating MCP launchers with a concrete pin suggestion
  (names the real package/image from `args` when present)
- `--resolve-pins` → with `--pins` or `--report`, look up exact npm/PyPI latest
  versions (5s timeout; Docker/Podman stay placeholders). Adds `resolved_pin` /
  `resolved_at` / `resolved_config_snippet` (trust-on-first-use). Default output
  without the flag is unchanged. Exit 2 without `--pins` or `--report`.
- `--report DIR` → single repo: write `reach-report.html` / `.md` / `.json` and
  `authority-sbom.json` (shareable audit artifact). HTML/MD open with a Summary
  (tier counts + top tier-2 findings + Pin fix when present); Honesty and
  Not-auto-inspected sit under Coverage and limits. JSON schema is unchanged.
- More than one `PATH` (requires `--report DIR`) → one fleet report
  (`auctelis.fleet_reach_report.v1`) with every repo ranked by tier-2 reach.
  Fleet writes `reach-report.html` / `.md` / `.json` only (no SBOM) and uses
  the same Summary-first layout, plus the ranked repo table.
  `--lock-file` and `--pins` apply to single-repo runs only
  (exit 2 if combined with multiple paths). `--baseline` is allowed on fleet.
- `--github TARGET ...` → zero-clone GitHub audit via Trees+Blobs API.
  Single `owner/repo` may omit `--report` (stdout check/pins/JSON); bare `org`
  or multiple targets require `--report DIR`. Lists non-archived, non-fork repos
  sorted by most recently pushed (capped by `--max-repos`, default 50; pass
  `--include-forks` to keep forks). Auth: `GITHUB_TOKEN` / `GH_TOKEN`, else
  `gh auth token` (unauthenticated public fallback). Fleet HTML/MD show
  skipped/truncated repos; GitHub-sourced reports include 1-click **Watch PRs**
  links (or **Watching** when `.github/workflows/auctelis*.yml` already exists).
  Labels reports as `owner/repo`, never temp paths. Fleet summaries lead with
  `auctelis rollout reach-report.json` (dry-run, then `--apply`).
- `--org-reusable ORG` → with `--report`, record ORG so `rollout` installs the
  6-line caller of
  `ORG/.github/.github/workflows/auctelis-org-reusable.yml@main`. Prefer
  `auctelis rollout REPORT_JSON --org-reusable ORG`. Exit 2 without `--report`
  or on an invalid org slug.
- `--baseline PATH` → prior `reach-report.json` (or `check --json` / fleet report)
  to diff when using `--report`. Single-repo and fleet / `--github` fleet runs
  are supported; schema mismatch exits 2. Fleet MD/HTML/summary gain
  **Changed since last audit** after Summary; JSON adds `baseline_diff` only
  when a baseline is given.
- `--max-files N` → inventory walk cap (default 50000; also `AUCTELIS_MAX_FILES`)
- `--strict-digests` → fail on plain-CI / prose representation digest drift
  (default: advisory note only; Hook body edits always fail)

`--json` emits `schema_version: authority-diff/1` plus `reach` (tier counts,
full `records`, and capped `top` / `top_cards`) and `pins`. With multiple paths
it emits the fleet document instead. With `--json --report`, stdout stays pure
JSON and the "Wrote reach report" note goes to stderr.

Exit codes: `0` quiet / first-run; `1` meaningful delta (any repo for fleet);
`2` unusable lock or invalid flag/path (any repo for fleet).

---

## `auctelis rollout`

```bash
auctelis rollout REPORT_JSON [--apply | --status] [--max-prs N] [--repo SLUG]
                             [--min-tier {1,2}] [--org-reusable ORG]
                             [--show-body] [--pin-sha | --action-sha SHA]
                             [--json] [--csv]
```

Reads `auctelis.fleet_reach_report.v1` or `auctelis.reach_report.v1` and
selects unwatched repos at or above `--min-tier` (default 2; cap 10). The
default is a dry-run: it prints the planned repos and workflow mode and makes
no HTTP writes. `--apply` uses `GITHUB_TOKEN` / `GH_TOKEN` / `gh auth token`
and stdlib HTTP (`GITHUB_API_URL` for GHES). It skips a repo that already has
`.github/workflows/auctelis*.yml` on the default branch, skips a repo with an
open pull request from `auctelis/watch-prs` (and prints that URL), creates or
reuses the branch, sends the existing blob `sha` when updating the workflow
file, and opens an evidence-backed pull request (tier counts, top findings,
literal `Pin fix` when available). `--repo owner/repo` (repeatable) targets
specific pilots. HTTP 403 or 422 tells you to run `gh auth refresh -s workflow`.
`--org-reusable ORG` commits the six-line caller instead of the inline lockless
workflow; when omitted, `org_reusable` from the Reach Report is used if set.
`--json` prints the plan. `--show-body` prints each dry-run Watch PR body
(the evidence-backed markdown); with `--json`, each result includes a `body`
field. `--pin-sha` looks up `roham-amd/auctelis` tag `v<this release>`
(`GET /git/ref/tags/vX`, then `GET /git/tags/<sha>` when the object is an
annotated tag) and writes `uses: roham-amd/auctelis@<40-hex> # vX` on lockless
Watch PRs. Lookup failure exits 2. `--action-sha <40-hex>` writes that same
pin with zero tag-lookup HTTP calls (uppercase hex is normalized to lowercase;
an invalid SHA exits 2). On GHES pass `--action-sha`; lookup stays on
`GITHUB_API_URL` and does not fall back to `https://api.github.com`. Both pin
flags are a no-op with `--org-reusable` and are mutually exclusive with
`--status` (exit 2). `--apply` is refused when `AUCTELIS_AGENT=1` (exit 2).
There is no auto-merge.

`--status` is a read-only funnel ledger (GET only; allowed under
`AUCTELIS_AGENT=1`). It reuses the same filters but **includes** already-watching
repos, then classifies each as `open` / `merged` / `closed_unmerged` /
`never_opened` / `watching_on_default` / `unknown`. Private-repo 404 →
`unknown`. HTTP 403 on `GET /pulls` names `Pull requests: read` in the detail.
Mutually exclusive with `--apply` (exit 2). `--csv` (requires
`--status`) emits a subset of `eval/pilot-metrics.csv` columns.

Exit codes: `0` dry-run / status, or every target opened or skipped; `1` a
target failed; `2` bad report, missing token, invalid flag, or agent refusal.

---

## `auctelis lock`

```bash
auctelis lock [PATH] [--check] [--update] [--lock-file PATH]
              [--accept-gated] [--max-files N] [--strict-digests]
```

Writes or verifies repo `AUTHORITY.lock`. `--check` is read-only. Writes are
refused when `AUCTELIS_AGENT=1` (speed bump, not a security control).
`--accept-gated` is compatibility-only on the product path: the inventory-only
scan carries no HIGH/CRITICAL findings, so it is a no-op (it matters only for a
findings-bearing `ScanResult` passed by maintainer code). It records no
approval — CODEOWNERS governs. Empty baseline is normal: first growth is
CODEOWNERS review, not forever `FAIL_CLOSED`. With `--check`, plain-CI / prose
representation digest drift is advisory unless `--strict-digests` (AUCT-034).

---

## `auctelis init`

```bash
auctelis init [PATH] --lockless [--force] [--pin-sha | --action-sha SHA]
auctelis init [PATH] --owner @TEAM [--force] [--enforce] [--advisory]
               [--pin-sha | --action-sha SHA]
```

`--lockless` writes only `.github/workflows/auctelis.yml` (the comment-only
Authority Diff workflow, pinned to this release) and exits. It needs no
`--owner` and writes no `.auctelis.yml`, CODEOWNERS, or `AUTHORITY.lock`; it
cannot be combined with `--enforce` (exit 2). This is the lowest-friction first
contact. `--pin-sha` rewrites the workflow to `uses: roham-amd/auctelis@<sha> # vX`
after resolving the release tag. `--action-sha <40-hex>` does the same offline
(no tag lookup; required on GHES). Both flags work with `--lockless` and with
`--owner` / `--enforce` (AUCT-057). An invalid `--action-sha` exits 2.

Without `--lockless`, `init` writes `.auctelis.yml`,
`.github/workflows/auctelis-gate.yml`, CODEOWNERS (including discovered
authority paths), and seals `AUTHORITY.lock`; `--owner` is required. Default
mode is **comment-only** (`locked: false`); pass `--enforce` for the locked
gate. `init` always merges CODEOWNERS and pins the Action to the release tag
(or to `--pin-sha` / `--action-sha` when given). Comment-only setup does not
probe rulesets; enforce setup probes them as a warning (files are still written).

---

## `auctelis gate`

```bash
auctelis gate [PATH] --base-lock PATH [--head-lock PATH]
              [--codeowners PATH] [--strict-ruleset | --no-strict-ruleset]
              [--skip-ruleset-check] [--trust-head-codeowners] [--max-files N]
              [--strict-digests]
              [--comment-only] [--comment-policy auto|always] [--agent]
```

Compares base→**tree-derived** head authority. `--head-lock` is drift-check
only (never the head snapshot). Pass a lock **file** to `--base-lock` (not a
directory). Growth with missing CODEOWNERS / unverified ruleset fails closed
when `--strict-ruleset` is on (default). Without a trusted base-ref CODEOWNERS
copy, pass `--trust-head-codeowners` (unsafe) or `--skip-ruleset-check` for
local use. CI should pass `--codeowners` from the base ref.

`--comment-only` keeps the required check green but reports `NEEDS_REVIEW` on
unreviewed tier-1+ growth (tier-0 instructions-only growth stays `PASS`).
`--comment-policy auto` (default) writes no
`pr-comment.md` on a quiet `PASS`/`NONE`; `always` posts on every run. On a quiet
run the gate also writes `comment-first-run.md`; the Action posts it only when
the PR has no sticky comment yet (first-run proof), then stays silent.

---

## `auctelis diff --base`

```bash
auctelis diff --base <git-ref> [--repo PATH] [--json]
auctelis diff lock <base.lock> <head.lock>
```

Local PR Authority Diff simulator: always extracts tree-truth authority from a
temporary detached worktree first (`baseline_state=tree`), matching the PR
Action. Falls back to a committed `AUTHORITY.lock` on the base ref
(`baseline_state=present`) only when worktree extract fails. When both succeed
and disagree, JSON sets `base_lock_drift=true` and text notes the drift.
Invalid ref → `FAIL_CLOSED`, exit 2. Regenerates head from the working tree and
prints the same comment dialect as the Action. Use `diff lock` to compare two
committed lock files directly.

---

## `auctelis why`

```bash
auctelis why NAME [PATH]
```

Prints the exact config path, destination, launcher, permissions, and
capabilities for one authority name. Default scope is the repository (`PATH`
or cwd).

Exit `1` when nothing matches.

---

## `auctelis trust`

```bash
auctelis trust <host> [host…] [--repo PATH]
auctelis trust --list [--repo PATH]
auctelis trust --remove <host> [host…] [--repo PATH]
auctelis trust --init [--repo PATH]
```

Writes `.auctelis/trusted-hosts` (one specific host per line; subdomains are
covered, but TLD-only and wildcard entries are rejected). Trusted destinations
lower **network-only** records to tier 1. New **MCP / Hook / Host Settings**
authority stays at tier 2 even when every destination is allowlisted; secrets,
execute, approvals, unattended, env-key, and launcher reach are never lowered.
`--init` writes an explicit starter list; nothing is trusted implicitly. In the gate, trust is
honored only when CODEOWNERS covers `.auctelis/trusted-hosts` (otherwise a PR
could allowlist its own destination); `init` writes that entry.

---

## `auctelis demo`

```bash
auctelis demo [-o DIR]
```

Runs the packaged vulnerable fixture and prints an Authority Diff. Always
exits `0` (walkthrough, not a gate).

---

## Maintainer (`auctelis-dev`)

```bash
auctelis-dev build all          # schemas, version parity, action parity, wheel lean
auctelis-dev build pypi-check   # Trusted Publishing cutover readiness (no publish)
auctelis-dev build schemas
auctelis-dev scan [PATH] [-o DIR] [--locked] [--base-lock PATH] [--fail-on never|high|any]
auctelis-dev annotate [findings.json] --format github|text|pr-comment
```

`build` / lint / corpus / deps stay maintainer-only. Annotation helpers are for
CI — not the product front door. Use `check` / `gate` / `diff --base` for
Authority Diff.

---

## Exit codes (summary)

| Command | `0` | `1` | `2` |
| --- | --- | --- | --- |
| `check` | quiet / first-run | meaningful delta | lock error |
| `lock --check` | matches | drift | — |
| `gate` | PASS (comment-only: also NEEDS_REVIEW) | NEEDS_REVIEW (enforce) | FAIL_CLOSED / usage |
| `diff --base` | PASS (or BASELINE_NEEDED only if tree extract failed) | NEEDS_REVIEW | FAIL_CLOSED / invalid ref |
| `rollout` | dry-run / status, or every target opened or skipped | a target failed | bad report / missing token / agent refusal / `--status --apply` / `--pin-sha --status` / `--action-sha --status` / invalid `--action-sha` / `--pin-sha` lookup failure |

`BASELINE_ADOPTED` is emitted by the Action wrapper when a head lock arrives with
no trusted base lock; the `gate` CLI itself returns `PASS` / `NEEDS_REVIEW` /
`FAIL_CLOSED`.

Agents must set `AUCTELIS_AGENT=1`; mutation commands (`lock`, `init`,
`rollout --apply`) are refused. That env var is a speed bump, not a security control.
