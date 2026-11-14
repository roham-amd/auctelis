# auctelis CLI reference

Primary command: **`auctelis`**.
Maintainer entry: **`auctelis-dev`** (build / lint / corpus / deps / validate / …).

Package `auctelis` **0.4.0** · product **0.4.0** · rule pack **1.6** (001–022).

Product contract / command tiers: [`PRODUCT.md`](PRODUCT.md) ·
lock semantics: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) ·
roadmap: [`ROADMAP.md`](ROADMAP.md).

Install: [`INSTALL.md`](INSTALL.md).

**Default:** bare `auctelis` runs `watch` (host authority delta). A path or scan
flags without a subcommand still run the hidden `scan`. Advanced commands remain
callable but are omitted from brief `--help`.

---

## Product command overview

| Tier | Command | Purpose |
| --- | --- | --- |
| Core | `watch` | One-screen declared authority delta vs `~/.auctelis/AUTHORITY.lock` |
| Core | `watch --seal` | Seal the human baseline (`lock --home` still works) |
| Core | `watch --arm` / `hook install` | Session + tool hooks for Cursor and Claude Code |
| Core | `hook status` | Wired / not firing |
| Core | `doctor` | Alias for `watch` |
| Core | `gate` | Label growth vs `--base-lock`; require CODEOWNERS + ruleset |
| Core | `ci init` | `.auctelis.yml` + workflow + CODEOWNERS + lock |
| Core | `demo` | First-run Authority Diff on packaged `demo-vulnerable` |
| Hidden | `scan` / `check` | Repo annotations (add `--locked`, `--full`) |
| Hidden | `vet` | Pre-install annotations for a local path or GitHub URL |
| Review | `harden` | Dry-run least-privilege patch proposals |
| Review | `explain` | Detailed explanation of a finding id |
| Review | `annotate` | GitHub annotations or Authority Diff PR comment |
| Review | `diff lock` | Record-level diff of two `AUTHORITY.lock` files |

Maintainer-only (`auctelis-dev`): `build`, `lint`, `deps`, `corpus`, `hosts`,
`validate`, `inventory`, `verify`, `export`, `run`, `snapshot`, `artifact-vet`.

---

## `auctelis watch`

```bash
auctelis watch [--home PATH] [--lock-file PATH] [--seal] [--arm]
               [--delta-only] [--json]
```

Inventories the host agent configs and prints one card per authority change:

```text
+ mcp "linear" → mcp.linear.app · network · tools · unpinned · publisher NOT VERIFIED
```

With no lock, the baseline is empty and every current record shows. After
`--seal`, an unchanged host prints `No authority change since you sealed` and
the session hook stays quiet. `--delta-only` prints only the changed lines (the
hook uses this). `--arm` installs the Cursor (`~/.cursor/hooks.json`) and Claude
(`~/.claude/settings.json`) hooks. `--json` emits the report.

Exit codes: `0` no change / no lock yet; `1` meaningful delta; `2` unusable
lock or internal error. `--seal` and `--arm` are refused when `AUCTELIS_AGENT=1`.

---

## `auctelis doctor`

```bash
auctelis doctor [--home PATH] [-o OUTPUT_DIR] [--fail-on never|high|any]
                 [--since-lock] [--delta-only] [--agent]
```

Alias for the `watch` screen. Reads local host configs under the user home
(`~/.cursor`, `~/.claude`, `~/.claude.json`, `~/.mcp.json`, `~/.vscode`,
`~/.codex`, Claude Desktop, Windsurf, Gemini, Zed). Local-only; nothing is
uploaded. Rule IDs are no longer the first screen.

---

## `auctelis hook`

```bash
auctelis hook install [--home PATH] [--hooks-dir PATH]
                      [--session-only | --pretool-only] [--no-wire] [--no-cursor]
auctelis hook status  [--home PATH] [--hooks-dir PATH] [--settings-file PATH]
                      [--cursor-hooks-file PATH] [--json]
```

`install` copies the session/tool hook scripts to `~/.auctelis/hooks`, wires
Claude Code `SessionStart` + `PreToolUse` (matcher `.*`), and wires Cursor
`sessionStart`, `beforeMCPExecution`, `beforeShellExecution`, `beforeFileEdit`.
`hook install` is a mutation and is refused for agents.

`status` reports `firing` / `not_firing` / `not_armed` / `not_wired` per host.
`not_armed` means wired but no `~/.auctelis/AUTHORITY.lock`; `not_firing` means a
script is missing or `auctelis` is not on PATH.

---

## `auctelis vet`

```bash
auctelis vet SOURCE [-o OUTPUT_DIR] [--keep-clone] [--agent]
```

`SOURCE` is a local path, Git URL, or `owner/repo` GitHub shorthand. Remote
sources are shallow-cloned with hooks disabled, no submodules, and no LFS
smudge. After the scan, remote clones quarantine project MCP/hooks configs by
renaming them to `*.auctelis-quarantined` (reported in the banner; useful with
`--keep-clone`). Exit `0` = `NO_FINDINGS_IN_SCOPE`; `1` = review/reject (incl.
unparsed configs); `2` = tooling failure (e.g. missing `git`). `--agent` prints
a fenced JSON digest.

---

## `auctelis demo`

```bash
auctelis demo [-o OUTPUT_DIR] [--fail-on never|high|any]
```

Scans the packaged `auctelis/data/demo-vulnerable` fixture (also available as
`examples/demo-vulnerable` in a checkout) and prints the Authority Diff PR
comment. Works from every supported install path, including a bare wheel.
Always exits `0` (tutorial / aha path).

---

## `auctelis lock`

```bash
auctelis lock [PATH] [--check] [--update] [--lock-file PATH]
              [--accept-gated] [--home] [--snapshot PATH] [--resolve]
```

Writes a sorted `AUTHORITY.lock` (v1) of authority records. `--check` regenerates
and exits `1` on drift (same as `auctelis check --locked`). `--accept-gated` is
required when the tree has HIGH/CRITICAL gated findings; it records no approval
and emits `approved_findings: []`. `--home` seals `~/.auctelis/AUTHORITY.lock`
and is an alias for `watch --seal`. `--snapshot` imports an MCP tools snapshot.
`--approval` is a deprecated no-op. Agents with `AUCTELIS_AGENT=1` cannot write
locks.

## `auctelis ci init`

```bash
auctelis ci init [PATH] --owner @TEAM [--force]
```

Writes `.auctelis.yml`, `.github/workflows/auctelis-gate.yml` (`locked: false` lockless-first),
`.github/CODEOWNERS` (with `--owner` for `AUTHORITY.lock`), and an
initial `AUTHORITY.lock` when the tree has **no** HIGH/CRITICAL gated findings.
If gated findings are present, templates may still be written but the lock is
**not** sealed — a human may explicitly run `auctelis lock --accept-gated`
(which records no approval) after review. Does not overwrite existing files
unless `--force`. `--owner` is required.

## `auctelis gate`

```bash
auctelis gate [PATH] --base-lock PATH [--head-lock PATH] [--codeowners PATH]
               [--skip-ruleset-check] [--strict-ruleset] [--agent]
```

Compares observed (or `--head-lock`) authority to an approved base lock. Labels
GROWTH vs REDUCTION. Exits `1` on growth when CODEOWNERS does not cover
`AUTHORITY.lock`, or when a ruleset probe returns `MISSING`. `--strict-ruleset`
is **on by default**, so `UNVERIFIED` also fails; use `--no-strict-ruleset` for
best-effort `PASS / protection unverified` (prominent warning — not the same as
verified protection). Reductions alone pass. An unparsed agent config or a
missing base/head lock fails closed. GitHub CODEOWNERS / rulesets enforce the
human review — auctelis does not count PR approvals. First-lock PRs with no
base lock are an Action **adoption ceremony** (`BASELINE_ADOPTED`), not a
growth-gate pass. `scan --base-lock` is advisory only; **gate** is the verdict.

---

## `auctelis harden`

```bash
auctelis harden [--findings PATH] [--apply]
```

Reads a prior `findings.json` and prints dry-run least-privilege patch templates
for high-confidence gated rules. `--apply` is rejected (exit `2`) in this
release — patches are never written automatically.

---

## `auctelis scan` / `check`

One-command Guard assessment of a repository tree.

```bash
auctelis scan [PATH] [-o OUTPUT_DIR] [--baseline PATH] [--save-baseline PATH]
         [--fail-on never|high|any] [--policy PATH] [--trust-target-policy]
         [--no-policy] [--locked] [--lock-file PATH] [--base-lock PATH]
         [--include-fixtures] [--full] [--agent]
```

| Flag | Meaning |
| --- | --- |
| `--fail-on` | `never` (default for bare scan unless policy), `high`, `any` |
| `--policy` | Explicit policy file (trusted) |
| `--trust-target-policy` | Discover `<target>/.auctelis.yml` |
| `--locked` | Fail when observed authority drifts from `AUTHORITY.lock` |
| `--base-lock` | Advisory head-vs-base lock delta (does **not** fail like `gate`) |
| `--full` | Also write graph, capabilities, long summary |
| `--agent` | Compact fenced JSON digest; default `-o` → `./auctelis-out` |

Default: target `.auctelis.yml` is **ignored** so third-party trees cannot blind
the scanner. Passive pack: AUCTELIS-RULE-001…022. See [`GUARD-SCAN.md`](GUARD-SCAN.md)
and [`SECURITY-RULES.md`](SECURITY-RULES.md).

### Artifacts (default)

`findings.json`, `findings.sarif.json` (artifact; not uploaded by default),
`inventory.json`, `authority-sbom.json`, `authority-snapshot.json`,
`scan-summary.txt`, `pr-comment.md`; `risk-delta.json` / `authority-delta.json`
when a baseline is supplied; `suppressions.json` when suppressions apply. With
`--full`: `ecosystem-graph.json`, `capabilities.json`, `scan-summary-full.txt`,
and related extras.

---

## `auctelis explain`

```bash
auctelis explain FINDING_ID -o OUTPUT_DIR [--agent]
```

Reads `OUTPUT_DIR/findings.json` and prints a human (or `--agent` JSON) explanation.

---

## `auctelis annotate`

```bash
auctelis annotate [FINDINGS.json] [--format github|text|pr-comment] [--risk-delta PATH]
```

| Argument | Default | Description |
| --- | --- | --- |
| `FINDINGS.json` | `auctelis-out/findings.json` | Guard findings document |
| `--format` | `github` | Actions workflow commands / plain text / Authority Diff |
| `--risk-delta` | — | Optional `risk-delta.json` for delta-first PR comments |

---

## `auctelis diff lock`

```bash
auctelis diff lock BASE.lock HEAD.lock
```

Record-level authority lock diff (`addition` / `removal` / `expansion` /
`reduction` / `replacement` / `policy_change`).

---

## Maintainer: `auctelis-dev`

Kill-list / non-product execute paths live here only (not on `auctelis`):

```bash
auctelis-dev build [all|schemas]
auctelis-dev validate report PATH [--no-semantic]
auctelis-dev inventory PATH [-o OUT.json]
auctelis-dev verify digest PATH [--expected HEX]
auctelis-dev export sarif REPORT_OR_FINDINGS.json [-o OUT.sarif.json]
auctelis-dev hosts list|show NAME
auctelis-dev corpus run
auctelis-dev deps outdated|upgrade [--dry-run]
auctelis-dev lint [--fix] [--format] [--check-format]
auctelis-dev run -- COMMAND [ARGS...]
auctelis-dev snapshot --from-file tools.json | --execute -- COMMAND...
auctelis-dev artifact-vet SPEC
```

`run` / `snapshot --execute` scrub a small allowlist of env vars only —
**not** a sandbox. Prefer `watch` / `watch --seal` / `watch --arm` / `hook status`
for the product path, with `lock` / `gate` as the team path.

- **build:** schema parity, version metadata, dependency pins, example validation, markdown link check
- **corpus:** deterministic tooling regression (`tests/corpus/`)
- **validate report:** JSON Schema + semantic refs on findings / report docs

---

## Library entry points

| Symbol | Module |
| --- | --- |
| `run_scan` | `auctelis.security.scan` |
| `run_security_scan` | `auctelis.security.engine` |
| `run_gate` | `auctelis.gate` |
| `build_authority_lock` / `diff_authority_locks` / `delta_label` | `auctelis.authority_lock` |
| `build_watch_report` / `seal_home_lock` | `auctelis.watch` |
| `install_hooks` / `hook_status` | `auctelis.hooks` |
| `collect_inventory` | `auctelis.inventory.collector` |
| `product_version` | `auctelis.versioning` |

---

## Related docs

- [`GUARD-SCAN.md`](GUARD-SCAN.md)
- [`../tools/README.md`](../tools/README.md)
- [`AUCTELIS-GATE.md`](AUCTELIS-GATE.md)
- [`.github/actions/auctelis-gate/action.yml`](../.github/actions/auctelis-gate/action.yml)
