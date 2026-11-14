# auctelis scan — annotation layer (hidden)

Guard scan path for **0.4.0**: deterministic discovery plus evidence-backed
observations via `auctelis scan` / `check`, with capability / exposure / finding
separation. This is an annotation layer behind the product, not the first
screen. Default terminal output is ≤15 lines (`--full` for the long report).
Artifacts land in cwd `./auctelis-out` (not inside the target tree).

Product front door: `auctelis watch` (one-screen authority delta) →
`auctelis watch --seal` → `auctelis watch --arm`.

Companion commands: `auctelis doctor` (alias for watch) and
`auctelis lock` (committed authority lockfile). `auctelis vet` remains callable
but is hidden.

Companion docs: [`PRODUCT.md`](PRODUCT.md), [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md),
[`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md), [`CLI-REFERENCE.md`](CLI-REFERENCE.md),
[`SECURITY-RULES.md`](SECURITY-RULES.md), [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md),
[`POLICY.md`](POLICY.md), [`AUCTELIS-GATE.md`](AUCTELIS-GATE.md).

---

## What Guard scan is

`auctelis scan` answers, for a local repository tree:

1. What agent-ecosystem components exist?
2. What security-relevant **capabilities** do they appear to have?
3. Which **deterministic rules** fire, with file evidence?
4. What remains **NOT VERIFIED** (coverage gaps)?
5. What changed vs **`AUTHORITY.lock`** (`--locked`) or a finding **baseline** (optional)?

### Lock vs baseline vs SBOM

| Artifact | Role |
| --- | --- |
| `AUTHORITY.lock` | **Product source of truth** for “what authority is approved”. CODEOWNERS-reviewed. |
| `baseline.json` | Finding/fingerprint risk delta for PR Authority Diff comments. |
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
│  auctelis scan    │  Deterministic facts + OBSERVED/POTENTIAL findings
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
# Recommended first command (git-tag install — see INSTALL.md):
auctelis watch
auctelis watch --seal
auctelis watch --arm

# Hidden annotation layer, when you explicitly want findings on a tree:
auctelis /path/to/target-repo
auctelis lock /path/to/target-repo
auctelis explain F-001 -o ./auctelis-out   # if findings exist
```

From a checkout:

```bash
cd tools && uv sync --locked
uv run auctelis demo
uv run auctelis scan /path/to/target-repo
```

Docker:

```bash
docker compose build
TARGET=/path/to/target-repo docker compose run --rm auctelis \
  scan /work -o /tmp/auctelis-out
```

---

## Pipeline internals

1. **Bounded inventory** — adapters walk the tree with file/depth/byte limits; refuse symlink escape; emit `inventory.json` + coverage matrix; attach content digests and fingerprints.
2. **Capability extraction** — map hints/types to capability kinds with explicit `origin` (`DECLARED` / `POTENTIAL` / `TYPE_DEFAULT`; never claim effective host permissions from type defaults alone).
3. **Rule engine** — apply versioned rules `AUCTELIS-RULE-001`…`022` (pack **1.6**) classifying each hit as `CAPABILITY`, `EXPOSURE`, or `SECURITY_FINDING` (see [`SECURITY-RULES.md`](SECURITY-RULES.md)).
4. **Evidence registry** — each finding references evidence with path, optional line span, content digest, and audited commit when known.
5. **Reporting** — authority snapshot + Markdown + JSON + SARIF; `auctelis explain` for one finding.
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

| Concern | `auctelis scan` | `auctelis-dev inventory` |
| --- | --- | --- |
| Deterministic findings | Yes | No (components only) |
| SARIF | Yes (artifact) | No |
| Default artifacts | PR comment, findings, inventory, SBOM | Inventory JSON |
| `--full` extras | Graph, capabilities, long reports | — |
| Recommended first command | **No** — hidden annotation layer | Maintainer discovery only |

Prefer `auctelis watch` for the weekly delta, and `auctelis lock` + `auctelis gate`
+ the CI Authority Diff for the team path.

---

## Baselines and continuous assessment

1. First assessment: `auctelis watch` then `auctelis watch --seal`.
2. After changes: `auctelis watch --delta-only` (or `auctelis check --locked .`).
3. Inspect `pr-comment.md` / lock delta for authority expansions.
4. CI: Action with `authority-diff: true` and `locked: false` (lockless-first);
   set `locked: true` after sealing `AUTHORITY.lock` (see
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
| `mode` | `scan` | Only `scan` is supported; other values do not run the scanner |
| `baseline` | — | Guard `baseline.json` |
| `baseline-inventory` | — | Optional inventory path diff |
| `fail-on` | empty → policy / never | `never` \| `high` \| `any` |
| `trusted-policy` | `true` | Load `.auctelis.yml` from PR base ref; fail on policy edits |
| `no-policy` | `false` | Ignore policy even if present |
| `authority-diff` | `true` | Build a base-ref baseline for the PR comment |
| `locked` | `false` | Run the base-lock growth gate after sealing |
| `lock-file` | `AUTHORITY.lock` | Lock path relative to the target |
| `strict-ruleset` | `true` | `UNVERIFIED` protection fails growth |
| `annotate` | `true` | Post annotations and the sticky PR comment |
| `output-dir` | `auctelis-out` | Artifact dir |
| `install-tools-from` | empty → Action-bundled tools | Prefer pinned kit; refuse accidental PR `./tools` |
| `upload-sarif` | `false` | Opt in to print the SARIF path for upload |

Hardening note: inputs are mapped to environment variables before bash uses them.
Never `uv sync` a PR-controlled `tools/` directory as the scanner.

---

## Optional AI explanation after scan

1. Attach [`../skills/auctelis-auditor/SKILL.md`](../skills/auctelis-auditor/SKILL.md).
2. Run `auctelis scan <target> --agent -o <OUT>/auctelis-out`.
3. Point the agent at `agent-digest.json` first, then `findings.json`.
4. Agent may run `auctelis explain` / dry-run `harden` only — never approve locks or edit policy.
5. Research/archive trees were removed in 0.3.0 — product path is
   `watch → watch --seal → watch --arm`, with `lock` + `gate` for the team path.

---

## Honesty and common misreads

| Misread | Correct interpretation |
| --- | --- |
| “0 findings ⇒ safe” | Incomplete coverage; many risks need host/runtime evidence |
| “HIGH finding ⇒ CVE” | Static configuration observation / potential path |
| “Graph edge ⇒ exploit” | Structural seed only |
| “CI green ⇒ production OK” | Only the configured policy thresholds passed |

Always keep the four questions separate: discovery, component trust, integration trust, production suitability.
