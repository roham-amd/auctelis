# authdiff 3.4 implementation backlog (historical)

> **Superseded for active work by [`GUARD-3.5-BACKLOG.md`](GUARD-3.5-BACKLOG.md)**
> (Authority Diff: `doctor` / `vet` / trusted PR gate). Kept for acceptance
> history of the 3.4 productization milestone.

Derived from the November 4, 2026 strategic product review.
North-star (then): **authdiff — Agent Ecosystem Security Gate** (local CLI + PR change gate).

Status key: `done` · `in_progress` · `next` · `deferred`

## Milestone L — Productization (3.4.0)

### L1 Product clarity and release foundation

| ID | Deliverable | Acceptance criteria | Status |
| --- | --- | --- | --- |
| L1.1 | Single product identity | README / release-manifest position authdiff as security change gate | done |
| L1.2 | Version consistency gate | `aesa build` fails if VERSION / versions.json / pyproject / `__init__` / release-manifest disagree | done |
| L1.3 | Default output outside target | `aesa scan` writes to cwd `./authdiff-out` unless `-o` / policy overrides; target tree not mutated by default | done |
| L1.4 | Skip self-artifacts in inventory | `authdiff-out*` directories excluded from traversal | done |
| L1.5 | Sample Guard report | `examples/guard-scan/` contains realistic scan artifacts | done |
| L1.6 | Installable package | `uv tool install` from Git works; PyPI OIDC workflow ready | done (git) / next (PyPI token) |
| L1.7 | Docs sync | All operator docs cite 3.4 positioning; 3.0/3.1 docs remain historical | in_progress |

### L2 Detection quality

| ID | Deliverable | Acceptance criteria | Status |
| --- | --- | --- | --- |
| L2.1 | Coverage transparency | Published `docs/COVERAGE-MATRIX.md` + adapter matrix in terminal report | done |
| L2.2 | Manual vs automated clarity | Browser / memory / models / multimodal marked MANUAL_ONLY in matrix | done |
| L2.3 | Rule fixture completeness | Every production rule has positive / negative / ambiguous fixtures | done (3.2) |
| L2.4 | Evidence line precision | High-severity findings carry path + line span + digest where readable | done (3.1+) |
| L2.5 | Host-specific detection | Expand Cursor / Claude Code effective-permission evidence | next |
| L2.6 | CI block policy clarity | Document which finding classes may fail CI | done (`docs/POLICY.md`) |

### L3 GitHub integration

| ID | Deliverable | Acceptance criteria | Status |
| --- | --- | --- | --- |
| L3.1 | `.authdiff.yml` policy | fail_on, baseline, output_dir, justified suppressions | done |
| L3.2 | Pin consumer example | Example workflow pins release tag/SHA, not `main` | done |
| L3.3 | Versioned Action release | Tagged composite Action with changelog notes | next |
| L3.4 | PR annotations | Annotate actionable findings at evidence locations | done |
| L3.5 | SARIF upload example | Documented code-scanning upload with minimal permissions | done |
| L3.6 | Blocking vs advisory modes | `policy.mode` + Action auto-load `.authdiff.yml` | done |

### L4 Adoption and validation

| ID | Deliverable | Acceptance criteria | Status |
| --- | --- | --- | --- |
| L4.1 | Pilot scans | Curated pilot harness + fixture/self pilots runnable | done (harness) |
| L4.2 | External review | Security reviewers inspect representative findings | next |
| L4.3 | Validation report | Transparent FP/FN / install-failure report published | next |
| L4.4 | Demo vulnerable repo | Fixture repo: finding → fix → PR gate | next |
| L4.5 | External benchmark N≥1 | Intake channel open; N=0 until independent submission | channel open |

## Explicitly deferred (do not start in 3.4)

- Hosted SaaS / web workbench
- Certification marketplace / public registry
- MCP audit-assistant server as primary product
- General runtime sandbox / penetration harness
- Expanding prompt framework as the main investment
- Broad AISVS compliance claims

## Suggested GitHub issues (create when ready)

1. Publish `authdiff` to PyPI with trusted publishing
2. Wire `.authdiff.yml` into `authdiff-gate` Action inputs automatically
3. PR review annotations from `findings.json` evidence spans
4. Expand host effective-permission adapters for Cursor + Claude Code
5. Demo repository + walkthrough for Guard PR gate
6. First external AgentSecBench intake drive

## Success metrics (90-day targets — aspirational)

| Metric | Target |
| --- | --- |
| Install → first useful scan | < 5 minutes |
| Weekly active repositories | 25+ |
| Repos with recurring PR integration | 10+ |
| High/Critical precision on blind reviewed cases | ≥ 90% |
| Unsupported `CONFIRMED` claims | 0 |
| Fixture coverage | Every production rule |
| Adapter coverage reporting | 100% of families in matrix |
