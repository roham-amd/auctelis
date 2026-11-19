# auctelis CLI reference

Primary command: **`auctelis`**.
Maintainer entry: **`auctelis-dev`** (build / lint / corpus / deps / validate / …).

Package `auctelis` **0.14.0** · product **0.14.0** · rule pack **1.6** (001–022).

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
| Core | `init --owner team` | One-command setup (policy + workflow + CODEOWNERS + lock) |
| Core | `check [--top N] [--pins] [--report DIR] [--baseline PATH] [--max-files N]` | Ranked reach report vs `AUTHORITY.lock` (front door); `--report` writes HTML+MD+JSON+SBOM |
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
`doctor`) and public `vet` / `harden` / `explain` CLIs were **removed** in 0.8.0.

---

## `auctelis check`

```bash
auctelis check [PATH] [--lock-file PATH] [--json] [--top N] [--pins]
               [--report DIR] [--baseline PATH] [--max-files N]
```

Inventories agent configs in a repository (MCP, skills, instructions, hooks,
rules, subagents, plugins, CI) and diffs them against the committed
`AUTHORITY.lock`. No host home scan. Prints a ranked reach summary and the top
five cards even when the lock matches (`--top 0` hides cards). `--report` always
lists every tier-2 record (not just the top cards).

- No lock yet → inventory + `BASELINE_NEEDED`; next step `auctelis lock --update`
- Lock matches → `LOCKED`, still showing reach counts and top cards
- Lock drifts → cards with `@ path` + `NEEDS_REVIEW`
- `--pins` → unpinned/floating MCP launchers with a concrete pin suggestion
- `--report DIR` → write `reach-report.html` / `.md` / `.json` and `authority-sbom.json` (shareable audit artifact)
- `--baseline PATH` → prior `reach-report.json` (or `check --json`) to diff when using `--report`
- `--max-files N` → inventory walk cap (default 50000; also `AUCTELIS_MAX_FILES`)

`--json` emits `schema_version: authority-diff/1` plus `reach` (tier counts,
full `records`, and capped `top` / `top_cards`) and `pins`.

Exit codes: `0` quiet / first-run; `1` meaningful delta; `2` unusable lock.

---

## `auctelis lock`

```bash
auctelis lock [PATH] [--check] [--update] [--lock-file PATH]
              [--accept-gated] [--max-files N]
```

Writes or verifies repo `AUTHORITY.lock`. `--check` is read-only. Writes are
refused when `AUCTELIS_AGENT=1` (speed bump, not a security control).
`--accept-gated` seals despite HIGH/CRITICAL annotations (records no approval —
CODEOWNERS governs). Empty baseline is normal: first growth is CODEOWNERS
review, not forever `FAIL_CLOSED`.

---

## `auctelis init` (preferred) / `ci init` (legacy alias)

```bash
auctelis init [PATH] --owner @TEAM [--force] [--enforce] [--advisory]
# legacy alias: auctelis ci init … [--apply]
```

Writes `.auctelis.yml`, `.github/workflows/auctelis-gate.yml`, CODEOWNERS
(including discovered authority paths), and seals `AUTHORITY.lock`. Default
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
unreviewed growth (never `PASS`). `--comment-policy auto` (default) writes no
`pr-comment.md` on a quiet `PASS`/`NONE`; `always` posts on every run. On a quiet
run the gate also writes `comment-first-run.md`; the Action posts it only when
the PR has no sticky comment yet (first-run proof), then stays silent.

---

## `auctelis diff --base`

```bash
auctelis diff --base <git-ref> [--repo PATH] [--json]
auctelis diff lock <base.lock> <head.lock>
```

Local PR Authority Diff simulator: resolves the git ref, reads committed
`AUTHORITY.lock` when present (`baseline_state=present`), otherwise extracts
tree-truth authority from a temporary detached worktree
(`baseline_state=tree`). Invalid ref → `FAIL_CLOSED`, exit 2. Regenerates head
from the working tree and prints the same comment dialect as the Action. JSON
includes `baseline_state`.

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
lower **network-only** records to tier 1, so benign MCP
additions stay on the comment instead of paging CODEOWNERS. Secrets, execute,
approvals, unattended, and env-key reach are never lowered. `--init` writes an
explicit starter list; nothing is trusted implicitly. In the gate, trust is
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

## Maintainer annotation (`auctelis-dev`)

```bash
auctelis-dev scan [PATH] [-o DIR] [--locked] [--base-lock PATH] [--fail-on never|high|any]
auctelis-dev annotate [findings.json] --format github|text|pr-comment
```

Artifact / SARIF / PR-comment helpers for CI. Not the product front door —
use `check` / `gate` / `diff --base` for Authority Diff.

---

## Exit codes (summary)

| Command | `0` | `1` | `2` |
| --- | --- | --- | --- |
| `check` | quiet / first-run | meaningful delta | lock error |
| `lock --check` | matches | drift | — |
| `gate` | PASS / BASELINE_ADOPTED (comment-only: also NEEDS_REVIEW) | NEEDS_REVIEW / FAIL_CLOSED (enforce) | usage |
| `diff --base` | PASS (or BASELINE_NEEDED only if tree extract failed) | NEEDS_REVIEW | FAIL_CLOSED / invalid ref |

Agents must set `AUCTELIS_AGENT=1`; mutation commands (`lock`, `ci init`) are
refused. That env var is a speed bump, not a security control.
