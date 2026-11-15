# auctelis CLI reference

Primary command: **`auctelis`**.
Maintainer entry: **`auctelis-dev`** (build / lint / corpus / deps / validate / …).

Package `auctelis` **0.8.1** · product **0.8.1** · rule pack **1.6** (001–022).

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
| Core | `check` | Repo authority vs `AUTHORITY.lock` (front door) |
| Core | `lock` | Write / check / update repo `AUTHORITY.lock` |
| Core | `ci init --apply --owner @team` | Enforce workflow + merge CODEOWNERS + verify ruleset |
| Core | `gate --base-lock base.lock` | PR Authority Diff + CODEOWNERS / ruleset gate |
| Core | `diff --base <ref>` | Local PR Authority Diff simulator |
| Core | `why <name>` | Exact config path / reach fields for one authority record |
| Core | `demo` | Packaged fixture walkthrough |
| Core | `diff lock` | Record-level diff of two `AUTHORITY.lock` files |

Maintainer-only (`auctelis-dev`): `scan`, `annotate`, `build`, `lint`, `deps`,
`corpus`, `hosts`, `validate`, `inventory`, `verify`, `export`, `run`,
`snapshot`, `artifact-vet`. The host stack (`watch` / `allow` / `hook` /
`doctor`) and public `vet` / `harden` / `explain` CLIs were **removed** in 0.8.0.

---

## `auctelis check`

```bash
auctelis check [PATH] [--lock-file PATH] [--json]
```

Inventories agent configs in a repository (MCP, skills, instructions, hooks,
rules, subagents, plugins, CI) and diffs them against the committed
`AUTHORITY.lock`. No host home scan.

- No lock yet → inventory + `BASELINE_NEEDED`; next step `auctelis lock --update`
- Lock matches → quiet `LOCKED`
- Lock drifts → cards with `@ path` + `NEEDS_REVIEW`

`--json` emits `schema_version: authority-diff/1`.

Exit codes: `0` quiet / first-run; `1` meaningful delta; `2` unusable lock.

---

## `auctelis lock`

```bash
auctelis lock [PATH] [--check] [--update] [--lock-file PATH]
              [--accept-gated]
```

Writes or verifies repo `AUTHORITY.lock`. `--check` is read-only. Writes are
refused when `AUCTELIS_AGENT=1` (speed bump, not a security control).
`--accept-gated` seals despite HIGH/CRITICAL annotations (records no approval —
CODEOWNERS governs). Empty baseline is normal: first growth is CODEOWNERS
review, not forever `FAIL_CLOSED`.

---

## `auctelis ci init`

```bash
auctelis ci init [PATH] --owner @TEAM [--force] [--advisory] [--apply]
```

Writes `.auctelis.yml`, `.github/workflows/auctelis-gate.yml`,
`.github/CODEOWNERS`, and attempts to seal `AUTHORITY.lock`. Default mode is
**enforce** (`locked: true`). Pass `--advisory` for warn-only.
`--apply` merges `AUTHORITY.lock` into an existing CODEOWNERS file, pins the
Action to a commit SHA when resolvable, and verifies ruleset protection
(exits `1` with the GitHub settings link when unverified).

---

## `auctelis gate`

```bash
auctelis gate [PATH] --base-lock PATH [--head-lock PATH]
              [--codeowners PATH] [--strict-ruleset | --no-strict-ruleset]
              [--skip-ruleset-check] [--trust-head-codeowners] [--agent]
```

Compares base→head authority. Pass a lock **file** to `--base-lock` (not a
directory). Growth with missing CODEOWNERS / unverified ruleset fails closed
when `--strict-ruleset` is on (default). Without a trusted base-ref CODEOWNERS
copy, pass `--trust-head-codeowners` (unsafe) or `--skip-ruleset-check` for
local use. CI should pass `--codeowners` from the base ref.

---

## `auctelis diff --base`

```bash
auctelis diff --base <git-ref> [--repo PATH] [--json]
auctelis diff lock <base.lock> <head.lock>
```

Local PR Authority Diff simulator: reads `AUTHORITY.lock` from the git ref via
`git show`, regenerates head from the working tree, and prints the same comment
dialect as the Action.

---

## `auctelis why`

```bash
auctelis why NAME [PATH] [--home PATH]
```

Prints the exact config path, destination, launcher, permissions, and
capabilities for one authority name. Default scope is the repository (`PATH`
or cwd). `--home` uses the archived host inventory instead.

Exit `1` when nothing matches.

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
| `gate` | PASS / BASELINE_ADOPTED | NEEDS_REVIEW / FAIL_CLOSED | usage |
| `diff --base` | PASS / none | NEEDS_REVIEW | FAIL_CLOSED |

Agents must set `AUCTELIS_AGENT=1`; mutation commands (`lock`, `ci init`) are
refused. That env var is a speed bump, not a security control.
