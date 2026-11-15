# auctelis CLI reference

Primary command: **`auctelis`**.
Maintainer entry: **`auctelis-dev`** (build / lint / corpus / deps / validate / …).

Package `auctelis` **0.7.0** · product **0.7.0** · rule pack **1.6** (001–022).

Product contract / command tiers: [`PRODUCT.md`](PRODUCT.md) ·
reach: [`REACH.md`](REACH.md) ·
lock semantics: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) ·
roadmap: [`ROADMAP.md`](ROADMAP.md).

Install: [`INSTALL.md`](INSTALL.md).

**Default:** bare `auctelis` runs `check` (repo authority vs `AUTHORITY.lock`).
A scanner-only flag without a subcommand (e.g. `--locked`) still routes to the
hidden `scan`. Advanced commands remain callable but are omitted from brief
`--help`.

---

## Product command overview

| Tier | Command | Purpose |
| --- | --- | --- |
| Core | `check` | Repo authority vs `AUTHORITY.lock` (front door; no host scan) |
| Core | `lock` | Write / check / update repo `AUTHORITY.lock` |
| Core | `ci init --owner @team` | Enforce workflow + CODEOWNERS + lock (`--advisory` opt-out) |
| Core | `gate --base-lock …` | PR Authority Diff + CODEOWNERS / ruleset gate |
| Core | `why <name>` | Exact config path / reach fields for one authority record |
| Core | `demo` | Packaged fixture walkthrough |
| Archived | `watch` | Host (+ project) sealable delta vs `~/.auctelis/AUTHORITY.lock` |
| Archived | `allow` | Decorative project-allow store (not enforced by hooks) |
| Archived | `hook install` / `hook status` | Tripwire install / heartbeat probe |
| Archived | `doctor` | Alias for `watch` |
| Hidden | `scan` | Repo annotations (add `--locked`, `--full`) |
| Hidden | `vet` | Pre-install annotations for a local path or GitHub URL |
| Review | `harden` | Dry-run least-privilege patch proposals |
| Review | `explain` | Detailed explanation of a finding id |
| Review | `annotate` | GitHub annotations or Authority Diff PR comment |
| Review | `diff lock` | Record-level diff of two `AUTHORITY.lock` files |

Maintainer-only (`auctelis-dev`): `build`, `lint`, `deps`, `corpus`, `hosts`,
`validate`, `inventory`, `verify`, `export`, `run`, `snapshot`, `artifact-vet`.

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
- Lock drifts → cards with `@ path` + `NEEDS_REVIEW` / `AUTHORITY_CHANGED`

`--json` emits `schema_version: authority-diff/1`.

Exit codes: `0` quiet / first-run; `1` meaningful delta; `2` unusable lock.

---

## `auctelis lock`

```bash
auctelis lock [PATH] [--check] [--update] [--lock-file PATH]
              [--accept-gated] [--home] [--snapshot PATH] [--resolve]
```

Writes or verifies repo `AUTHORITY.lock`. `--check` is read-only. Writes are
refused when `AUCTELIS_AGENT=1`. `--accept-gated` seals despite HIGH/CRITICAL
annotations (records no approval — CODEOWNERS governs). `--home` seals host
authority under `~/.auctelis/AUTHORITY.lock` (archived personal path).

---

## `auctelis ci init`

```bash
auctelis ci init [PATH] --owner @TEAM [--force] [--advisory]
```

Writes `.auctelis.yml`, `.github/workflows/auctelis-gate.yml`,
`.github/CODEOWNERS`, and attempts to seal `AUTHORITY.lock`. Default mode is
**enforce** (`locked: true`). Pass `--advisory` for warn-only.

---

## `auctelis gate`

```bash
auctelis gate [PATH] --base-lock PATH [--head-lock PATH]
              [--codeowners PATH] [--strict-ruleset | --no-strict-ruleset]
              [--skip-ruleset-check] [--agent]
```

Compares base→head authority. Growth with missing CODEOWNERS / unverified
ruleset fails closed when `--strict-ruleset` is on (default).

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

## Archived: `watch` / `allow` / `hook` / `doctor`

These remain fully callable for compatibility. They are **not** the product
path (see [`PRODUCT.md`](PRODUCT.md) kill list).

### `auctelis watch`

```bash
auctelis watch [--home PATH] [--project PATH] [--lock-file PATH]
               [--seal] [--accept DIGEST] [--arm] [--delta-only] [--json]
```

Host (+ optional project) authority vs `~/.auctelis/AUTHORITY.lock`. First run
shows every sealable record + Accept digest. `--seal` requires matching
`--accept`. `--arm` installs tripwire hooks. `--json` → `watch-report/1`.

### `auctelis allow`

```bash
auctelis allow [PATH] [--home PATH] [--accept DIGEST] [--status] [--json]
```

Writes `~/.auctelis/project-allow.json`. Decorative status only — tripwires do
not enforce it.

### `auctelis hook`

```bash
auctelis hook install [--session-only|--pretool-only] [--no-wire] [--no-cursor]
auctelis hook status [--probe] [--json]
```

Copies session/PreToolUse scripts and optionally wires Claude/Cursor settings.
`--probe` fires a synthetic unknown MCP through the scripts (not proof of host
wiring). Heartbeats are shared-session stamps — treat status as advisory.

### `auctelis doctor`

Alias for `watch` (host map). Prefer `check` for repositories.

---

## Hidden: `scan` / `vet`

```bash
auctelis scan [PATH] [-o DIR] [--locked] [--base-lock PATH] [--fail-on never|high|any]
              [--full] [--agent] [--trust-target-policy] …
auctelis vet SOURCE [-o DIR] [--keep-clone] [--agent]
```

Annotation layer: findings, SARIF, risk delta. Not the Authority Diff product.
Use `gate` for growth verdicts.

---

## Review helpers

| Command | Purpose |
| --- | --- |
| `diff lock BASE HEAD` | Record-level lock diff |
| `annotate [findings.json] --format github\|text\|pr-comment` | Annotations / PR body |
| `explain FINDING_ID` | Finding detail from `auctelis-out/` |
| `harden --findings PATH` | Dry-run least-privilege proposals |

---

## Exit codes (summary)

| Command | `0` | `1` | `2` |
| --- | --- | --- | --- |
| `check` | quiet / first-run | meaningful delta | lock error |
| `lock --check` | matches | drift | — |
| `gate` | PASS / BASELINE_ADOPTED | NEEDS_REVIEW / FAIL_CLOSED | usage |
| `watch` | quiet / first-run | sealed delta | lock / seal error |

Agents must set `AUCTELIS_AGENT=1`; mutation commands (`lock`, `ci init`,
`watch --seal/--arm`, `allow`, `hook install`) are refused.
