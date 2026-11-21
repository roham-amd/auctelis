# auctelis CLI reference

Primary command: **`auctelis`**.
Maintainer entry: **`auctelis-dev`** (build / lint / corpus / deps / validate / …).

Package `auctelis` **0.1.0** · product **0.1.0** · rule pack **1.6** (001–022).

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
| Core | `check [PATH ...] [--top N] [--pins] [--report DIR] [--baseline PATH] [--max-files N] [--github TARGET …] [--max-repos N] [--include-forks]` | Ranked reach report vs `AUTHORITY.lock` (front door); `--github` zero-clone org/repo audit; multi-path / multi-repo = fleet report |
| Core | `trust <host>` | Trusted destinations for network-only reach |
| Core | `status [--check]` | Lock / workflow / CODEOWNERS / protection summary |
| Core | `lock` | Write / check / update repo `AUTHORITY.lock` |
| Core | `gate --base-lock base.lock` | Tree-truth PR Authority Diff + CODEOWNERS gate |
| Core | `diff --base <ref>` | Local PR Authority Diff simulator |
| Core | `why <name>` | Exact config path / reach fields for one authority record |
| Core | `demo` | Packaged fixture walkthrough |
| Core | `diff lock` | Record-level diff of two `AUTHORITY.lock` files |
| Legacy | `ci init` | Alias of `init` |

Maintainer-only (`auctelis-dev`): `scan`, `annotate`, `build`, `lint`, `deps`,
`corpus`, `hosts`, `validate`, `inventory`, `verify`, `export`, `run`,
`snapshot`, `artifact-vet`. The host stack (`watch` / `allow` / `hook` /
`doctor`) and public `vet` / `harden` / `explain` CLIs were **removed**.

---

## `auctelis check`

```bash
auctelis check [PATH ...] [--lock-file PATH] [--json] [--top N] [--pins]
               [--report DIR] [--baseline PATH] [--max-files N]
               [--github TARGET ...] [--max-repos N] [--include-forks]
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
- `--report DIR` → single repo: write `reach-report.html` / `.md` / `.json` and
  `authority-sbom.json` (shareable audit artifact)
- More than one `PATH` (requires `--report DIR`) → one fleet report
  (`auctelis.fleet_reach_report.v1`) with every repo ranked by tier-2 reach.
  Fleet writes `reach-report.html` / `.md` / `.json` only (no SBOM).
  `--lock-file`, `--baseline`, and `--pins` apply to single-repo runs only
  (exit 2 if combined with multiple paths)
- `--github TARGET ...` → zero-clone GitHub audit via Trees+Blobs API.
  Single `owner/repo` may omit `--report` (stdout check/pins/JSON); bare `org`
  or multiple targets require `--report DIR`. Lists non-archived, non-fork repos
  sorted by most recently pushed (capped by `--max-repos`, default 50; pass
  `--include-forks` to keep forks). Auth: `GITHUB_TOKEN` / `GH_TOKEN`, else
  `gh auth token` (unauthenticated public fallback). Fleet HTML/MD show
  skipped/truncated repos; GitHub-sourced reports include 1-click **Watch PRs**
  links (or **Watching** when `.github/workflows/auctelis*.yml` already exists).
  Labels reports as `owner/repo`, never temp paths.
- `--baseline PATH` → prior `reach-report.json` (or `check --json`) to diff when using `--report`
- `--max-files N` → inventory walk cap (default 50000; also `AUCTELIS_MAX_FILES`)

`--json` emits `schema_version: authority-diff/1` plus `reach` (tier counts,
full `records`, and capped `top` / `top_cards`) and `pins`. With multiple paths
it emits the fleet document instead. With `--json --report`, stdout stays pure
JSON and the "Wrote reach report" note goes to stderr.

Exit codes: `0` quiet / first-run; `1` meaningful delta (any repo for fleet);
`2` unusable lock or invalid flag/path (any repo for fleet).

---

## `auctelis lock`

```bash
auctelis lock [PATH] [--check] [--update] [--lock-file PATH]
              [--accept-gated] [--max-files N]
```

Writes or verifies repo `AUTHORITY.lock`. `--check` is read-only. Writes are
refused when `AUCTELIS_AGENT=1` (speed bump, not a security control).
`--accept-gated` is compatibility-only on the product path: the inventory-only
scan carries no HIGH/CRITICAL findings, so it is a no-op (it matters only for a
findings-bearing `ScanResult` passed by maintainer code). It records no
approval — CODEOWNERS governs. Empty baseline is normal: first growth is
CODEOWNERS review, not forever `FAIL_CLOSED`.

---

## `auctelis init` (preferred) / `ci init` (legacy alias)

```bash
auctelis init [PATH] --lockless [--force]
auctelis init [PATH] --owner @TEAM [--force] [--enforce] [--advisory]
# legacy alias: auctelis ci init … [--apply] (also accepts --lockless)
```

`--lockless` writes only `.github/workflows/auctelis.yml` (the comment-only
Authority Diff workflow, pinned to this release) and exits. It needs no
`--owner` and writes no `.auctelis.yml`, CODEOWNERS, or `AUTHORITY.lock`; it
cannot be combined with `--enforce` (exit 2). This is the lowest-friction first
contact.

Without `--lockless`, `init` writes `.auctelis.yml`,
`.github/workflows/auctelis-gate.yml`, CODEOWNERS (including discovered
authority paths), and seals `AUTHORITY.lock`; `--owner` is required. Default
mode is **comment-only** (`locked: false`); pass `--enforce` for the locked
gate. `init` always merges CODEOWNERS and pins the Action to the release tag
(the `--apply` flag exists only on the `ci init` alias and is accepted there for
backwards compatibility). Comment-only setup does not probe rulesets; enforce
setup probes them as a warning (files are still written).

---

## `auctelis gate`

```bash
auctelis gate [PATH] --base-lock PATH [--head-lock PATH]
              [--codeowners PATH] [--strict-ruleset | --no-strict-ruleset]
              [--skip-ruleset-check] [--trust-head-codeowners] [--max-files N]
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

`BASELINE_ADOPTED` is emitted by the Action wrapper when a head lock arrives with
no trusted base lock; the `gate` CLI itself returns `PASS` / `NEEDS_REVIEW` /
`FAIL_CLOSED`.

Agents must set `AUCTELIS_AGENT=1`; mutation commands (`lock`, `init`, `ci init`)
are refused. That env var is a speed bump, not a security control.
