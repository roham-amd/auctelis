# auctelis-dev scan — annotation layer (maintainer)

> **Maintainer research surface (`auctelis-dev`). Not part of the product gate.**
> Product path: [`PRODUCT.md`](PRODUCT.md) — check → diff --base →
> lockless workflow or init --enforce → gate.

Guard scan path for maintainers: deterministic discovery plus evidence-backed
observations via `auctelis-dev scan` / `annotate`, with capability / exposure /
finding separation. This is an annotation layer behind the product, not the
first screen. Default terminal output is ≤15 lines (`--full` for the long
report). Artifacts land in cwd `./auctelis-out` (not inside the target tree).

Product front door: `auctelis check` → `auctelis diff --base <ref>` →
(`auctelis init --lockless` or `auctelis init --owner team [--enforce]`) →
PR `gate`. Public `scan` / `vet` / `explain` / `watch` / `allow` / `hook`
CLIs are **removed**.

Companion docs: [`PRODUCT.md`](PRODUCT.md), [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md),
[`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md), [`CLI-REFERENCE.md`](CLI-REFERENCE.md),
[`SECURITY-RULES.md`](SECURITY-RULES.md), [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md),
[`POLICY.md`](POLICY.md), [`AUCTELIS-GATE.md`](AUCTELIS-GATE.md).

---

## What Guard scan is

`auctelis-dev scan` answers, for a local repository tree:

1. What agent-ecosystem components exist?
2. What security-relevant **capabilities** do they appear to have?
3. Which **deterministic rules** fire, with file evidence?
4. What remains **NOT VERIFIED** (coverage gaps)?
5. What changed vs **`AUTHORITY.lock`** (`--locked`) or a finding **baseline** (optional)?

### Lock vs baseline vs SBOM

| Artifact | Role |
| --- | --- |
| `AUTHORITY.lock` | **Product source of truth** for “what authority is approved”. CODEOWNERS-reviewed. |
| `baseline.json` | Legacy maintainer-only finding/fingerprint baseline; not an Action input since 0.14. |
| `authority-sbom.json` | Export of observed authority components (advisory inventory, not a lock). |

It does **not**:

- Execute target code, install dependencies, or contact MCP/production endpoints
- Prove exploits or issue a global “secure/insecure” verdict
- Replace host IAM, network policy, or human risk acceptance
- Guarantee complete discovery (adapters have maturity levels)

---

## Hybrid responsibility model

```text
Repository (untrusted data)
        │
        ▼
┌───────────────────┐
│  auctelis-dev scan│  Deterministic facts + OBSERVED/POTENTIAL findings
│  (core engine)    │
└─────────┬─────────┘
          │ auctelis-out/
          ▼
┌───────────────────┐
│  Optional AI      │  Explain evidence; never source of truth
│  (auditor skill)  │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Human operator   │  Scope, acceptance, authority approval
└───────────────────┘
```

Principle: never ask an LLM to establish a fact the CLI can establish; never let an unsupported LLM claim become an enforced finding.

---

## First-run workflow (target: under 10 minutes)

```bash
# Product front door (git-tag install — see INSTALL.md):
auctelis check
auctelis lock --update
auctelis init --owner security

# Maintainer annotation only (not the product gate):
auctelis-dev scan /path/to/target-repo -o ./auctelis-out
```

From a checkout:

```bash
cd tools && uv sync --locked
uv run auctelis demo
uv run auctelis check /path/to/target-repo
```

Docker is not the Authority Diff install path. Prefer the git-tag / release wheel.

---

## Pipeline internals

1. **Bounded inventory** — adapters walk the tree with file/depth/byte limits; refuse symlink escape; emit `inventory.json` + coverage matrix; attach content digests and fingerprints.
2. **Capability extraction** — map hints/types to capability kinds with explicit `origin` (`DECLARED` / `POTENTIAL` / `TYPE_DEFAULT`; never claim effective host permissions from type defaults alone).
3. **Rule engine** — apply versioned rules `AUCTELIS-RULE-001`…`022` (pack **1.6**) classifying each hit as `CAPABILITY`, `EXPOSURE`, or `SECURITY_FINDING` (see [`SECURITY-RULES.md`](SECURITY-RULES.md)).
4. **Evidence registry** — each finding references evidence with path, optional line span, content digest, and audited commit when known.
5. **Reporting** — authority snapshot + Markdown + JSON + SARIF (maintainer artifacts).
6. **Optional baseline delta** — fingerprint-aware comparison; CI `--fail-on` ignores pure capability observations.

---

## Output directory layout

```text
auctelis-out/
├── inventory.json           # components + coverage.adapter_matrix
├── findings.json            # findings, evidence_registry, capabilities, summary
├── findings.sarif.json      # artifact only; Action upload is opt-in
├── authority-sbom.json      # authority SBOM
├── authority-snapshot.json  # canonical component snapshot
├── scan-summary.txt         # human terminal report
├── pr-comment.md            # one-verdict Authority Diff
├── baseline.json            # only with `scan --save-baseline`
└── risk-delta.json          # when `--baseline` supplied
```

With `--full`, add `ecosystem-graph.json`, `capabilities.json`,
`scan-report.md`, `scan-summary-full.txt`, and `profile.json`.

### Terminal report sections

- Ecosystem summary (component count, authority-bearing, external destinations, high-priority candidates)
- Components by type
- Findings (severity/confidence, evidence path, recommended action)
- Coverage / NOT VERIFIED
- Honesty footer (observations ≠ confirmed exploits)

### `findings.json` top-level fields

| Field | Meaning |
| --- | --- |
| `findings_version` | Guard findings document version (`1.2`) |
| `product` / `product_version` / `package_version` | auctelis identity |
| `repository` / `audited_commit` | Exact assessed tree |
| `rules_applied` | Rule ids executed |
| `summary` | Counts and severity histogram |
| `capabilities` | Extracted capability records |
| `evidence_registry` | Evidence objects |
| `findings` | Finding objects |
| `relationships` | Cross-component composites (skill↔MCP, hook↔MCP) |
| `coverage` | From inventory, including `unparsed_agent_config_count` |
| `suppressions` / `suppression_count` | Explicit suppression audit trail |
| `target_policy_ignored` | Target `.auctelis.yml` was not trusted |
| `limitations` | Explicit non-claims |

---

## Scan vs inventory

| Concern | `auctelis-dev scan` | `auctelis-dev inventory` |
| --- | --- | --- |
| Deterministic findings | Yes | No (components only) |
| SARIF | Yes (artifact) | No |
| Default artifacts | PR comment, findings, inventory, SBOM | Inventory JSON |
| `--full` extras | Graph, capabilities, long reports | — |
| Recommended first command | **No** — hidden annotation layer | Maintainer discovery only |

Prefer `auctelis check` for the weekly delta, and `auctelis lock` + `auctelis gate`
+ the CI Authority Diff for the team path. Host tripwires and public scanner CLIs
are removed — use `auctelis-dev scan` in CI / maintainer workflows only.

---

## Baselines and continuous assessment

1. First assessment: `auctelis check` then `auctelis lock --update`.
2. After changes: `auctelis check` (or `auctelis diff --base origin/main`).
3. Inspect `pr-comment.md` / lock delta for authority expansions.
4. CI: lockless comment-only first (`locked: false`); set `locked: true` after sealing if you want enforce
   `AUTHORITY.lock` (see
   [`auctelis-consumer-gate.example.yml`](auctelis-consumer-gate.example.yml)).

Baseline identity is **fingerprint-first** (content digest of authority-bearing
evidence), with path/name as a secondary signal. Renames of unchanged content
should not look like new risk; treat residual churn as a review signal, not
absolute truth.

---

## CI integration (auctelis Action)

Composite action: [`.github/actions/auctelis-gate`](../.github/actions/auctelis-gate) (display name: auctelis).

| Input | Default | Notes |
| --- | --- | --- |
| `path` | `.` | Target path (passed via env, not shell-interpolated) |
| `mode` | `scan` | Only `scan` is supported; any other value fails the job loudly |
| `trusted-policy` | `true` | Fail edits to an existing `.auctelis.yml` unless base-ref CODEOWNERS covers it |
| `authority-diff` | `true` | Extract base-ref tree authority for the Authority Diff gate |
| `locked` | `false` | Comment-only default; set `true` / `init --enforce` to fail on growth |
| `lock-file` | `AUTHORITY.lock` | Lock path relative to the target |
| `strict-ruleset` | empty | Locked-aware default (`true` when `locked=true`, else `false`) |
| `comment-on-none` | `false` | Post the Authority Diff even when authority did not change (default: quiet on `NONE`, sticky updated once) |
| `output-dir` | `auctelis-out` | Artifact dir |
| `install-tools-from` | empty → Action-bundled tools | Prefer pinned kit; refuse accidental PR `./tools` |

Deprecated research inputs (`baseline`, `baseline-inventory`, `fail-on`,
`no-policy`, `annotate`, `upload-sarif`) were **removed in 0.14.0**.

Hardening note: inputs are mapped to environment variables before bash uses them.
Never `uv sync` a PR-controlled `tools/` directory as the scanner.

---

## Optional AI explanation after check / gate

1. Attach [`../skills/auctelis-auditor/SKILL.md`](../skills/auctelis-auditor/SKILL.md).
2. Run `auctelis check` / `auctelis diff --base <ref>` / `auctelis gate` (read-only).
3. Point the agent at the Authority Diff cards (`--json` or PR comment).
4. Agent may explain the delta only — never run `lock`, never mutate policy.
5. Product path: `check → diff --base → init --lockless / init --owner team → gate`.

---

## Honesty and common misreads

| Misread | Correct interpretation |
| --- | --- |
| “0 findings ⇒ safe” | Incomplete coverage; many risks need host/runtime evidence |
| “HIGH finding ⇒ CVE” | Static configuration observation / potential path |
| “Graph edge ⇒ exploit” | Structural seed only |
| “CI green ⇒ production OK” | Only the configured policy thresholds passed |

Always keep the four questions separate: discovery, component trust, integration trust, production suitability.
