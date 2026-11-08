# authdiff CLI reference

Primary command: **`authdiff`**. Compatibility alias: **`authdiff`**.
Maintainer entry: **`authdiff-dev`** (build / lint / corpus / benchmark / …).

Package `authdiff` **1.0.0** · product **1.0.0** · rule pack **1.6** (001–022).

Product contract / command tiers: [`PRODUCT.md`](PRODUCT.md) ·
lock semantics: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) ·
roadmap: [`ROADMAP.md`](ROADMAP.md).

Install: [`INSTALL.md`](INSTALL.md).

**Default:** bare `authdiff` (or a path / scan flags without a subcommand) runs
`scan .`. Advanced commands remain callable but are omitted from brief `--help`.

---

## Product command overview

| Tier | Command | Purpose |
| --- | --- | --- |
| Core | `demo` | First-run Authority Diff on `examples/demo-vulnerable` |
| Core | `doctor` | Host authority map (Cursor / Claude / VS Code / …) |
| Core | `vet` / `open` | Pre-install verdict for a local path or GitHub URL |
| Core | `scan` / `check` / bare `authdiff` | Repo findings + SARIF (add `--locked`, `--full`) |
| Core | `lock` | Write / update / `--check` `AUTHORITY.lock` |
| Core | `ci init` / `init-gate` | `.authdiff.yml` + workflow + CODEOWNERS + lock |
| Review | `delta` | New-only authority gate vs `--baseline` |
| Review | `harden` / `fix` | Dry-run least-privilege patch proposals |
| Review | `explain` | Detailed explanation of a finding id |
| Review | `baseline` | Save / show finding baselines (≠ lock) |
| Review | `annotate` | GitHub annotations or Authority Diff PR comment |
| Review | `diff lock` | Record-level diff of two `AUTHORITY.lock` files |
| Review | `diff risk` | Finding risk delta vs baseline |
| Advanced | `init-manifest` / `verify-manifest` | Experimental `AUTHORITY.yml` |
| Advanced | `run` / `snapshot` / `artifact-vet` / `atlas` / `lsp-validate` | Opt-in |

Maintainer-only (`authdiff-dev`): `build`, `lint`, `deps`, `corpus`, `benchmark`,
`pilots`, `hosts`, `validate`, `graph`, `inventory`, `audit`, `preflight`, `verify`,
`export`.

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

## `authdiff vet` / `open`

```bash
authdiff vet SOURCE [-o OUTPUT_DIR] [--keep-clone] [--agent]
authdiff open SOURCE   # alias
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
Default `--fail-on high`.

---

## `authdiff lock`

```bash
authdiff lock [PATH] [--check] [--update] [--lock-file PATH] [--approval OWNER]
```

Writes a sorted `AUTHORITY.lock` (v2) of authority records. `--check` regenerates
and exits `1` on drift (same as `authdiff check --locked`). `--approval OWNER`
appends a human approval record bound to the sealed `lock_hash`, commit, and
policy hash. Protect the file with CODEOWNERS; prefer this over long-term
reliance on suppressions alone. Agents with `AUTHDIFF_AGENT=1` cannot write locks.

## `authdiff ci init` / `init-gate`

```bash
authdiff ci init [PATH] [--force]
```

Writes `.authdiff.yml`, `.github/workflows/authdiff-gate.yml` (`locked: true`),
`.github/CODEOWNERS` (placeholder `@YOUR_TEAM` for `AUTHORITY.lock`), and an
initial `AUTHORITY.lock`. Does not overwrite existing files unless `--force`.

---

## `authdiff harden`

```bash
authdiff harden [--findings PATH] [--apply]
```

Reads a prior `findings.json` and prints dry-run least-privilege patch templates
for high-confidence gated rules. `--apply` is rejected (exit `2`) in this
release — patches are never written automatically.

---

## `authdiff init-manifest` / `authdiff verify-manifest`

```bash
authdiff init-manifest [PATH] [--force]
authdiff verify-manifest [PATH] [-o REPORT.json]
```

`init-manifest` drafts `AUTHORITY.yml` from observed inventory (declared vs
observed). `verify-manifest` fails when undeclared components appear. Matching
a declaration is **not** a security clearance.

---

## `authdiff scan`

One-command Guard assessment of a repository tree.

```bash
authdiff scan [PATH] [-o OUTPUT_DIR] [--baseline PATH] [--save-baseline PATH]
         [--fail-on never|high|any] [--policy PATH] [--no-policy] [--agent]
```

| Argument | Default | Description |
| --- | --- | --- |
| `PATH` | `.` | Target repository root (read-only traversal) |
| `-o` / `--output-dir` | `./authdiff-out` (cwd) | Artifact directory (not under target by default) |
| `--baseline` | — / `.authdiff.yml` | Prior `baseline.json` for risk delta |
| `--save-baseline` | — | Write baseline after scan |
| `--fail-on` | `never` or `.authdiff.yml` | Exit `1` when policy matches |
| `--policy` | `.authdiff.yml` inside scan target only | Explicit policy path (never parent dirs outside target) |
| `--no-policy` | off | Ignore `.authdiff.yml` |
| `--agent` | off | Print compact fenced agent digest (+ write `agent-digest.json`) |

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success (or findings present but policy `never`) |
| `1` | Policy failure (`high` / `any`) |
| `2` | CLI usage error |

### Artifacts written

| File | Description |
| --- | --- |
| `inventory.json` | Discovered components + coverage |
| `ecosystem-graph.json` | Structural graph seed |
| `findings.json` | Guard findings, evidence registry, capabilities |
| `capabilities.json` | Capability extraction subset |
| `findings.sarif.json` | SARIF 2.1.0 |
| `scan-summary.txt` | Terminal report (also printed) |
| `scan-report.md` | Markdown summary |
| `pr-comment.md` | ≤12-line Authority Diff PR comment |
| `profile.json` | Scan metadata + rules applied |
| `risk-delta.json` | Only when `--baseline` is provided |
| `agent-digest.json` | Only when `--agent` is set |

Details: [`GUARD-SCAN.md`](GUARD-SCAN.md), rules: [`SECURITY-RULES.md`](SECURITY-RULES.md).

### Examples

```bash
authdiff scan .
authdiff scan /repos/app -o /tmp/authdiff-out --fail-on high
authdiff scan . --baseline authdiff-out/baseline.json --save-baseline authdiff-out/baseline.json
```

---

## `authdiff explain`

```bash
authdiff explain FINDING_ID [-o OUTPUT_DIR] [--agent]
```

Reads `OUTPUT_DIR/findings.json` (default `authdiff-out`) and prints attack-path reasoning, evidence, missing controls, and recommended action for `F-001`, etc. `--agent` emits structured remediation JSON with fenced evidence strings.

---

## `authdiff baseline`

```bash
authdiff baseline save [-o OUTPUT_DIR] [--path BASELINE.json]
authdiff baseline show [BASELINE.json]
```

`save` re-scans the repository recorded in `findings.json` (or uses the output dir parent) and writes a baseline of component keys + finding keys for future risk deltas.

Default baseline path: `<output-dir>/baseline.json`.

---

## `authdiff audit`

```bash
authdiff audit [PATH] [--profile quick|standard|deployment] [-o OUTPUT_DIR]
```

| Profile | Purpose | Deep review handoff | Deployment worksheet |
| --- | --- | --- | --- |
| `quick` | Inventory + prioritization | No | No |
| `standard` | Deeper agent handoff (default) | Yes | No |
| `deployment` | Production suitability worksheet | Yes | Yes |

### Artifacts

`inventory.json`, `ecosystem-graph.json`, `audit-context.md`, `audit-summary.md`, `preflight-summary.md`, `profile.json`, and optionally `deployment-worksheet.md`.

Prefer **`authdiff scan`** for security observations; use **`audit`** when preparing an AI agent deep-review package.

---

## `authdiff preflight`

```bash
authdiff preflight [PATH] [-o OUTPUT_DIR]
```

Alias of `authdiff audit --profile quick` (2.3 compatibility).

---

## `authdiff inventory`

```bash
authdiff inventory PATH [-o OUTPUT.json]
```

Passive discovery only. Prints JSON to stdout unless `-o` is set.

---

## `authdiff validate`

```bash
authdiff validate report PATH [--no-semantic]
authdiff validate graph PATH [--no-semantic]
authdiff validate claim PATH
```

| Subcommand | Checks |
| --- | --- |
| `report` | JSON Schema + semantic refs (evidence ids, component ids) |
| `graph` | Graph schema + semantic edge/node consistency |
| `claim` | Structured claim object; `CONFIRMED` requires non-empty `evidence_ids` |

Exit `0` on OK, `1` on validation failure.

---

## `authdiff graph paths`

```bash
authdiff graph paths PATH.json
```

Prints auto-discovered structural path candidates from an ecosystem graph JSON. Paths are **not** confirmed attack proofs.

---

## `authdiff diff`

```bash
authdiff diff report BASE.json TARGET.json
authdiff diff graph BASE.json TARGET.json
authdiff diff risk BASELINE.json FINDINGS.json
```

| Kind | Compares |
| --- | --- |
| `report` | Component / finding id sets and severity/title changes |
| `graph` | Edge keys added/removed |
| `risk` | Guard baseline vs current findings (prefer re-scan when repo path exists) |

---

## `authdiff export sarif`

```bash
authdiff export sarif REPORT_OR_FINDINGS.json [-o OUT.sarif.json]
```

Accepts audit-report JSON or Guard `findings.json`. Tool name in SARIF: **authdiff**.

Note: `authdiff scan` already writes `findings.sarif.json`.

---

## `authdiff annotate`

```bash
authdiff annotate [FINDINGS.json] [--format github|text|pr-comment] [--risk-delta PATH]
```

| Argument | Default | Description |
| --- | --- | --- |
| `FINDINGS.json` | `authdiff-out/findings.json` | Guard findings document |
| `--format` | `github` | `github` = Actions workflow commands; `text` = plain lines; `pr-comment` = ≤12-line Authority Diff |
| `--risk-delta` | — | Optional `risk-delta.json` for delta-first PR comments |

`github`/`text` emit annotations only for `SECURITY_FINDING` / `EXPOSURE` (never pure `CAPABILITY`). Target-derived strings in `pr-comment` are markdown-escaped. The GitHub Action runs annotations after scan when `annotate: true` and posts the Authority Diff comment to the job summary.

---

## `authdiff pilots`

```bash
authdiff pilots list [--manifest PATH]
authdiff pilots run [--manifest PATH] [-o OUT_DIR] [--only ID ...]
```

Runs curated adoption scans from [`archive/pilots/manifest.json`](archive/pilots/manifest.json)
(`authdiff-dev pilots`). Pilot results are **not** AgentSecBench external evidence.
See [`archive/pilots/README.md`](archive/pilots/README.md).

---

## `authdiff verify`

```bash
authdiff verify digest PATH [--expected HEX]
authdiff verify manifest PATH [-o OUT.json]
```

Passive SHA-256 helpers. See [`../tools/authdiff/supply_chain/README.md`](../tools/authdiff/supply_chain/README.md).

---

## `authdiff-dev build`

```bash
authdiff build [all|schemas|prompts] [--write]
```

| Target | Behavior |
| --- | --- |
| `all` | Schema parity, version metadata, dependency pins, example validation, monolith check |
| `schemas` | Copy canonical audit-report schema to published aliases |
| `prompts` | Check or (`--write`) regenerate `archive/methodology/prompts/audit.full.md` |

---

## `authdiff hosts`

```bash
authdiff hosts list
authdiff hosts show cursor
authdiff hosts show claude-code
```

Lists built-in host assessment profiles. Profiles describe **declared** configuration surfaces; effective permissions remain NOT VERIFIED without host/runtime evidence.

---

## `authdiff-dev corpus` / `authdiff-dev benchmark`

```bash
authdiff corpus run
authdiff benchmark run
authdiff benchmark rules
authdiff benchmark governance
authdiff benchmark contract verify
authdiff benchmark submitter-package -o DIR
authdiff benchmark intake DIR --agent-id ID [--provenance external|pilot|sample|template] [--dry-run]
authdiff benchmark intakes
authdiff benchmark collection-status
authdiff benchmark llm --validate-only [--split public|held_out|all]
authdiff benchmark llm --submissions DIR [--split …] [--report] [--provenance external|any|…]
```

- **Corpus:** deterministic tooling regression (`tests/corpus/`, CORPUS-001…010).
- **`benchmark run`:** inventory + Guard rule smoke cases (`tests/benchmark/cases`).
- **`benchmark rules`:** per-rule positive/negative/ambiguous quality pack (`tests/rules/`).
- **`benchmark governance`:** LLM dataset checksums and version pins.
- **`benchmark contract`:** frozen evaluation contract verification.
- **`benchmark submitter-package`:** task cards without ground truth for external submitters.
- **`benchmark intake` / `intakes`:** validate, checksum, and preserve submissions as untrusted data (never execute); list external evidence.
- **`benchmark collection-status`:** invitations vs responses vs valid intakes (zeros until outreach yields evidence).
- **`benchmark llm`:** offline scoring / transparent report (never calls model APIs). Templates/pilots are not external evidence.

Exit `0` if all cases pass, `1` otherwise.

---

## `authdiff deps`

```bash
authdiff deps outdated
authdiff deps upgrade [--dry-run]
```

Compares / refreshes `tools/uv.lock` against PyPI. Does not rewrite human constraints in `pyproject.toml` except via normal `uv` workflows.

---

## `authdiff-dev lint`

```bash
authdiff lint [--fix] [--format] [--check-format]
```

Runs Ruff on `tools/authdiff` and `tests`.

---

## Library entry points

| Symbol | Module |
| --- | --- |
| `run_scan` | `authdiff.security.scan` |
| `run_security_scan` | `authdiff.security.engine` |
| `run_audit` | `authdiff.audit` |
| `collect_inventory` | `authdiff.inventory.collector` |
| `product_version` | `authdiff.versioning` |

---

## Related docs

- [`GUARD-SCAN.md`](GUARD-SCAN.md)
- [`../tools/README.md`](../tools/README.md)
- [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md)
- [`.github/actions/authdiff-gate/action.yml`](../.github/actions/authdiff-gate/action.yml)
