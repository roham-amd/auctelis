# authdiff CLI reference

Primary command: **`authdiff`**.
Maintainer entry: **`authdiff-dev`** (build / lint / corpus / deps / validate / …).

Package `authdiff` **0.3.3** · product **0.3.3** · rule pack **1.6** (001–022).

Product contract / command tiers: [`PRODUCT.md`](PRODUCT.md) ·
lock semantics: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) ·
roadmap: [`ROADMAP.md`](ROADMAP.md).

Install: [`INSTALL.md`](INSTALL.md).

**Default:** bare `authdiff` runs `doctor` when the cwd has no `AUTHORITY.lock` /
`.authdiff.yml`; otherwise `scan .`. A path or scan flags without a subcommand
still run `scan`. Advanced commands remain callable but are omitted from brief
`--help`.

---

## Product command overview

| Tier | Command | Purpose |
| --- | --- | --- |
| Core | `demo` | First-run Authority Diff on packaged `demo-vulnerable` |
| Core | `doctor` | Host authority map (Cursor / Claude / VS Code / …) |
| Core | `vet` | Pre-install verdict for a local path or GitHub URL |
| Core | `scan` / `check` / bare `authdiff` | Repo findings + SARIF; bare → doctor or scan (add `--locked`, `--full`) |
| Core | `lock` | Write / update / `--check` `AUTHORITY.lock` |
| Core | `gate` | Label growth vs `--base-lock`; require CODEOWNERS + ruleset |
| Core | `ci init` | `.authdiff.yml` + workflow + CODEOWNERS + lock |
| Review | `harden` | Dry-run least-privilege patch proposals |
| Review | `explain` | Detailed explanation of a finding id |
| Review | `annotate` | GitHub annotations or Authority Diff PR comment |
| Review | `diff lock` | Record-level diff of two `AUTHORITY.lock` files |

Maintainer-only (`authdiff-dev`): `build`, `lint`, `deps`, `corpus`, `hosts`,
`validate`, `inventory`, `verify`, `export`, `run`, `snapshot`, `artifact-vet`.

---

## `authdiff doctor`

```bash
authdiff doctor [--home PATH] [-o OUTPUT_DIR] [--fail-on never|high|any] [--agent]
```

Reads local host configs under the user home (`~/.cursor`, `~/.claude`,
`~/.mcp.json`, `~/.vscode`, `~/.codex`). Local-only; nothing is uploaded.
Lone config files are staged redacted under a throwaway dir (never copied raw
into `-o`). `$HOME` is never scanned wholesale. `--agent` needs `-o` so surface
`findings.json` files remain available.

---

## `authdiff vet`

```bash
authdiff vet SOURCE [-o OUTPUT_DIR] [--keep-clone] [--agent]
```

`SOURCE` is a local path, Git URL, or `owner/repo` GitHub shorthand. Remote
sources are shallow-cloned with hooks disabled, no submodules, and no LFS
smudge. After the scan, remote clones quarantine project MCP/hooks configs by
renaming them to `*.authdiff-quarantined` (reported in the banner; useful with
`--keep-clone`). Exit `0` = `NO_FINDINGS_IN_SCOPE`; `1` = review/reject (incl.
unparsed configs); `2` = tooling failure (e.g. missing `git`). `--agent` prints
a fenced JSON digest.

---

## `authdiff demo`

```bash
authdiff demo [-o OUTPUT_DIR] [--fail-on never|high|any]
```

Scans the packaged `authdiff/data/demo-vulnerable` fixture (also available as
`examples/demo-vulnerable` in a checkout) and prints the Authority Diff PR
comment. Works from every supported install path, including a bare wheel.
Always exits `0` (tutorial / aha path).

---

## `authdiff lock`

```bash
authdiff lock [PATH] [--check] [--update] [--lock-file PATH] [--approval OWNER]
              [--accept-gated] [--home] [--snapshot PATH] [--resolve]
```

Writes a sorted `AUTHORITY.lock` (v1) of authority records. `--check` regenerates
and exits `1` on drift (same as `authdiff check --locked`). `--accept-gated` is
required when the tree has HIGH/CRITICAL gated findings; optional `--approval`
only adds an `acceptance_note` on those findings (not a gate input). `--home`
seals `~/.authdiff/AUTHORITY.lock`. `--snapshot` imports an MCP tools snapshot.
Protect the file with CODEOWNERS; GitHub rulesets enforce review. Agents with
`AUTHDIFF_AGENT=1` cannot write locks.

## `authdiff ci init`

```bash
authdiff ci init [PATH] --owner @TEAM [--force]
```

Writes `.authdiff.yml`, `.github/workflows/authdiff-gate.yml` (`locked: true`),
`.github/CODEOWNERS` (with `--owner` for `AUTHORITY.lock`), and an
initial `AUTHORITY.lock` when the tree has **no** HIGH/CRITICAL gated findings.
If gated findings are present, templates may still be written but the lock is
**not** sealed — run `authdiff lock --accept-gated` (records accepted rule IDs)
after a human review. Does not overwrite existing files unless `--force`.
`--owner` is required.

## `authdiff gate`

```bash
authdiff gate [PATH] --base-lock PATH [--head-lock PATH] [--codeowners PATH]
               [--skip-ruleset-check] [--strict-ruleset]
```

Compares observed (or `--head-lock`) authority to an approved base lock. Labels
GROWTH vs REDUCTION. Exits `1` on growth when CODEOWNERS does not cover
`AUTHORITY.lock`, or when a ruleset probe returns `MISSING`. With
`--strict-ruleset`, `UNVERIFIED` also fails; otherwise growth can `PASS /
protection unverified` (prominent warning — not the same as verified
protection). Reductions alone pass. GitHub CODEOWNERS / rulesets enforce the
human review — authdiff does not count PR approvals. First-lock PRs with no
base lock are an Action **adoption ceremony** (`BASELINE_ADOPTED`), not a
growth-gate pass. `scan --base-lock` is advisory only; **gate** is the verdict.

---

## `authdiff harden`

```bash
authdiff harden [--findings PATH] [--apply]
```

Reads a prior `findings.json` and prints dry-run least-privilege patch templates
for high-confidence gated rules. `--apply` is rejected (exit `2`) in this
release — patches are never written automatically.

---

## `authdiff scan` / `check`

One-command Guard assessment of a repository tree.

```bash
authdiff scan [PATH] [-o OUTPUT_DIR] [--baseline PATH] [--save-baseline PATH]
         [--fail-on never|high|any] [--policy PATH] [--trust-target-policy]
         [--no-policy] [--locked] [--base-lock PATH] [--full] [--agent]
```

| Flag | Meaning |
| --- | --- |
| `--fail-on` | `never` (default for bare scan unless policy), `high`, `any` |
| `--policy` | Explicit policy file (trusted) |
| `--trust-target-policy` | Discover `<target>/.authdiff.yml` |
| `--locked` | Fail when observed authority drifts from `AUTHORITY.lock` |
| `--base-lock` | Advisory head-vs-base lock delta (does **not** fail like `gate`) |
| `--full` | Also write graph, capabilities, long summary |
| `--agent` | Compact fenced JSON digest; default `-o` → `./authdiff-out` |

Default: target `.authdiff.yml` is **ignored** so third-party trees cannot blind
the scanner. Passive pack: AUTHDIFF-RULE-001…022. See [`GUARD-SCAN.md`](GUARD-SCAN.md)
and [`SECURITY-RULES.md`](SECURITY-RULES.md).

### Artifacts (default)

`findings.json`, `findings.sarif.json`, `inventory.json`, `scan-summary.txt`,
`pr-comment.md`. With `--full`: `ecosystem-graph.json`, `capabilities.json`,
`scan-summary-full.txt`, and related extras.

---

## `authdiff delta`

```bash
authdiff delta [PATH] --baseline BASELINE.json [-o OUTPUT_DIR] [--fail-on …]
```

Alias of `scan` that requires `--baseline` for finding / fingerprint risk-delta.
This is **not** the same as `gate --base-lock` (authority growth gate).

---

## `authdiff explain`

```bash
authdiff explain FINDING_ID -o OUTPUT_DIR [--agent]
```

Reads `OUTPUT_DIR/findings.json` and prints a human (or `--agent` JSON) explanation.

---

## `authdiff annotate`

```bash
authdiff annotate [FINDINGS.json] [--format github|text|pr-comment] [--risk-delta PATH]
```

| Argument | Default | Description |
| --- | --- | --- |
| `FINDINGS.json` | `authdiff-out/findings.json` | Guard findings document |
| `--format` | `github` | Actions workflow commands / plain text / Authority Diff |
| `--risk-delta` | — | Optional `risk-delta.json` for delta-first PR comments |

---

## `authdiff diff lock`

```bash
authdiff diff lock BASE.lock HEAD.lock
```

Record-level authority lock diff (`addition` / `removal` / `expansion` /
`reduction` / `replacement` / `policy_change`).

---

## Advanced: `run` / `snapshot` / `artifact-vet`

```bash
authdiff run -- COMMAND [ARGS...]
authdiff snapshot --from-file tools.json | --execute -- COMMAND...
authdiff artifact-vet SPEC
```

`run` / `snapshot --execute` scrub a small allowlist of env vars only —
**not** a sandbox. Prefer `scan` / `lock` / `gate` for product workflows.

---

## Maintainer: `authdiff-dev`

```bash
authdiff-dev build [all|schemas]
authdiff-dev validate report PATH [--no-semantic]
authdiff-dev inventory PATH [-o OUT.json]
authdiff-dev verify digest PATH [--expected HEX]
authdiff-dev export sarif REPORT_OR_FINDINGS.json [-o OUT.sarif.json]
authdiff-dev hosts list|show NAME
authdiff-dev corpus run
authdiff-dev deps outdated|upgrade [--dry-run]
authdiff-dev lint [--fix] [--format] [--check-format]
```

- **build:** schema parity, version metadata, dependency pins, example validation, markdown link check
- **corpus:** deterministic tooling regression (`tests/corpus/`)
- **validate report:** JSON Schema + semantic refs on findings / report docs

---

## Library entry points

| Symbol | Module |
| --- | --- |
| `run_scan` | `authdiff.security.scan` |
| `run_security_scan` | `authdiff.security.engine` |
| `run_gate` | `authdiff.gate` |
| `build_authority_lock` / `diff_authority_locks` | `authdiff.authority_lock` |
| `collect_inventory` | `authdiff.inventory.collector` |
| `product_version` | `authdiff.versioning` |

---

## Related docs

- [`GUARD-SCAN.md`](GUARD-SCAN.md)
- [`../tools/README.md`](../tools/README.md)
- [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md)
- [`.github/actions/authdiff-gate/action.yml`](../.github/actions/authdiff-gate/action.yml)
