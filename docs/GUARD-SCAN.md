# authdiff scan — operator guide

Guard scan path for **1.0.0**: deterministic discovery plus evidence-backed
observations via `authdiff scan` / `check`, with capability / exposure / finding
separation. Default terminal output is ≤15 lines (`--full` for the long report).
Artifacts land in cwd `./authdiff-out` (not inside the target tree).

Companion commands: `authdiff doctor`, `authdiff open` / `vet`, and
`authdiff lock` (committed authority lockfile).

Companion docs: [`PRODUCT.md`](PRODUCT.md), [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md),
[`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md), [`CLI-REFERENCE.md`](CLI-REFERENCE.md),
[`SECURITY-RULES.md`](SECURITY-RULES.md), [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md),
[`POLICY.md`](POLICY.md), [`AUTHDIFF-GATE.md`](AUTHDIFF-GATE.md).

---

## What Guard scan is

`authdiff scan` answers, for a local repository tree:

1. What agent-ecosystem components exist?
2. What security-relevant **capabilities** do they appear to have?
3. Which **deterministic rules** fire, with file evidence?
4. What remains **NOT VERIFIED** (coverage gaps)?
5. What changed vs **`AUTHORITY.lock`** (`--locked`) or a finding **baseline** (optional)?

### Lock vs baseline vs AUTHORITY.yml

| Artifact | Role |
| --- | --- |
| `AUTHORITY.lock` | **Product source of truth** for “what authority is approved”. CODEOWNERS-reviewed. |
| `baseline.json` | Finding/fingerprint risk delta for PR Authority Diff comments. |
| `AUTHORITY.yml` | Experimental declared-vs-observed manifest (`init-manifest`). |

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
│  authdiff scan    │  Deterministic facts + OBSERVED/POTENTIAL findings
│  (core engine)    │
└─────────┬─────────┘
          │ authdiff-out/
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
# Recommended first command (git-tag uvx or uv tool install — see INSTALL.md):
authdiff demo

# Against a real tree (bare `authdiff` defaults to `scan .`):
authdiff /path/to/target-repo
authdiff lock /path/to/target-repo
authdiff explain F-001 -o ./authdiff-out   # if findings exist
```

From a checkout:

```bash
cd tools && uv sync --locked
uv run authdiff demo
uv run authdiff scan /path/to/target-repo
```

Docker:

```bash
docker compose build
TARGET=/path/to/target-repo docker compose run --rm authdiff \
  scan /work -o /tmp/authdiff-out
```

---

## Pipeline internals

1. **Bounded inventory** — adapters walk the tree with file/depth/byte limits; refuse symlink escape; emit `inventory.json` + coverage matrix; attach content digests and fingerprints.
2. **Capability extraction** — map hints/types to capability kinds with explicit `origin` (`DECLARED` / `POTENTIAL` / `TYPE_DEFAULT`; never claim effective host permissions from type defaults alone).
3. **Rule engine** — apply versioned rules `AUTHDIFF-RULE-001`…`022` (pack **1.5**) classifying each hit as `CAPABILITY`, `EXPOSURE`, or `SECURITY_FINDING` (see [`SECURITY-RULES.md`](SECURITY-RULES.md)).
4. **Evidence registry** — each finding references evidence with path, optional line span, content digest, and audited commit when known.
5. **Reporting** — authority snapshot + Markdown + JSON + SARIF; `authdiff explain` for one finding.
6. **Optional baseline delta** — fingerprint-aware comparison; CI `--fail-on` ignores pure capability observations.

---

## Output directory layout

```text
authdiff-out/
├── inventory.json           # components + coverage.adapter_matrix
├── ecosystem-graph.json     # structural seed (not attack-path proof)
├── findings.json            # findings, evidence_registry, capabilities, summary
├── capabilities.json        # capabilities array
├── findings.sarif.json      # SARIF 2.1.0 for CI / code scanning upload
├── scan-summary.txt         # human terminal report
├── scan-report.md           # Markdown wrapper + executive questions
├── profile.json             # product/version/rules/limitations
├── baseline.json            # after `authdiff baseline save` or `--save-baseline`
└── risk-delta.json          # when `--baseline` supplied
```

### Terminal report sections

- Ecosystem summary (component count, authority-bearing, external destinations, high-priority candidates)
- Components by type
- Findings (severity/confidence, evidence path, recommended action)
- Coverage / NOT VERIFIED
- Honesty footer (observations ≠ confirmed exploits)

### `findings.json` top-level fields

| Field | Meaning |
| --- | --- |
| `findings_version` | Guard findings document version (`1.0`) |
| `product` / `product_version` / `package_version` | authdiff identity |
| `repository` / `audited_commit` | Exact assessed tree |
| `rules_applied` | Rule ids executed |
| `summary` | Counts and severity histogram |
| `capabilities` | Extracted capability records |
| `evidence_registry` | Evidence objects |
| `findings` | Finding objects |
| `coverage` | From inventory |
| `limitations` | Explicit non-claims |

---

## Scan vs audit profiles

| Concern | `authdiff scan` | `authdiff audit --profile …` (advanced) |
| --- | --- | --- |
| Deterministic findings | Yes | No (inventory + handoff only) |
| SARIF | Yes | Via separate export of a later report |
| Default artifacts | PR comment, findings, inventory, SARIF | Rich audit-context handoff |
| `--full` extras | Graph, capabilities, long reports | — |
| Recommended first command | **Yes** (`authdiff demo` then `scan`) | Maintainer / deep-review only |

Prefer `authdiff lock` + CI Authority Diff over legacy `audit` profiles.

---

## Baselines and continuous assessment

1. First assessment: `authdiff scan .` then `authdiff lock`.
2. After changes: `authdiff check --locked .` (or `scan --baseline authdiff-out/baseline.json`).
3. Inspect `pr-comment.md` / lock delta for authority expansions.
4. CI: Action with `authority-diff: true` and `locked: true` (see [`authdiff-consumer-gate.example.yml`](authdiff-consumer-gate.example.yml)).

Baseline identity is **fingerprint-first** (content digest of authority-bearing
evidence), with path/name as a secondary signal. Renames of unchanged content
should not look like new risk; treat residual churn as a review signal, not
absolute truth.

---

## CI integration (authdiff Action)

Composite action: [`.github/actions/authdiff-gate`](../.github/actions/authdiff-gate) (display name: authdiff).

| Input | Default | Notes |
| --- | --- | --- |
| `path` | `.` | Target path (passed via env, not shell-interpolated) |
| `mode` | `scan` | `scan` or legacy `audit` |
| `profile` | `quick` | Only for `mode=audit` |
| `baseline` | — | Guard `baseline.json` |
| `baseline-inventory` | — | Optional inventory path diff |
| `fail-on` | empty → policy / never | `never` \| `high` \| `any` |
| `trusted-policy` | `true` | Load `.authdiff.yml` from PR base ref; fail on policy edits |
| `output-dir` | `authdiff-out` | Artifact dir |
| `install-tools-from` | empty → Action-bundled tools | Prefer pinned kit; refuse accidental PR `./tools` |
| `upload-sarif` | `true` | Prints SARIF path for optional upload |

Hardening note: inputs are mapped to environment variables before bash uses them.
Never `uv sync` a PR-controlled `tools/` directory as the scanner.

---

## Optional AI explanation after scan

1. Attach [`../skills/authdiff-auditor/SKILL.md`](../skills/authdiff-auditor/SKILL.md).
2. Run `authdiff scan <target> --agent -o <OUT>/authdiff-out`.
3. Point the agent at `agent-digest.json` first, then `findings.json`.
4. Agent may run `authdiff explain` / dry-run `harden` only — never approve locks or edit policy.
5. Archived methodology under `archive/methodology/` is **not** on the product path.

---

## Honesty and common misreads

| Misread | Correct interpretation |
| --- | --- |
| “0 findings ⇒ safe” | Incomplete coverage; many risks need host/runtime evidence |
| “HIGH finding ⇒ CVE” | Static configuration observation / potential path |
| “Graph edge ⇒ exploit” | Structural seed only |
| “CI green ⇒ production OK” | Only the configured policy thresholds passed |

Always keep the four questions separate: discovery, component trust, integration trust, production suitability.
