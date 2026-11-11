# authdiff roadmap

**Product:** the authority lockfile and PR security gate for AI agents  
**Current:** 0.3.0 / tooling 0.3.0 / rule pack 1.6  


This roadmap applies the strategic diagnosis: keep building around
`AUTHORITY.lock` + PR Authority Diff + CI gate. Do not expand into a
generic AI security platform, SaaS dashboard, marketplace, or runtime
firewall until adoption of the core gate is proven.

---

## North star

> Know what authority your AI agents have, what changes when integrations
> are introduced, and whether those changes have been approved.

| Stage | Meaning |
| --- | --- |
| Discover | Deterministic inventory of agent-related authority |
| Lock | Versioned record of approved authority |
| Diff | Meaningful classification when authority changes |
| Approve | Human + CODEOWNERS review |
| Enforce | CI gate with base-ref trusted policy |

---

## Product ranking (committed vs deferred)

| Rank | Direction | Status |
| --- | --- | --- |
| 1 | Authority Lock + PR Gate | **Primary product** |
| 2 | GitHub Action as CI surface | Ship with #1 (`locked` default **true**) |
| 3 | One-command local CLI | Core path: demo → doctor → scan → lock → ci init |
| 4 | Pre-install vet (`open` / `vet`) | Companion entry |
| 5 | Agent Authority Manifest / SBOM | Shipped MVP (`AUTHORITY.yml` + `authority-sbom.json`) |
| 6 | Thin coding-agent skill | `skills/authdiff-auditor` |
| 7–12 | MCP audit server, web app, marketplace, runtime broker, heavy AgentSecBench | **Deferred** |

AgentSecBench remains research infrastructure. Do not cite it as independent
validation while external submissions remain N=0.

---

## 30-day plan — status (applied through 0.3.0)

### Days 1–3 · Gate truth (0.3.0)

- [x] `scan --base-lock` is advisory; `authdiff gate` is the only growth verdict
- [x] Action posts comment/summary/artifacts with `if: always()`, then fails on scan/gate codes
- [x] Six-scenario gate harness (`tests/test_gate_scenarios.py`)
- [x] Dogfood: `AUTHORITY.lock`, `.authdiff.yml`, CODEOWNERS, local Action workflow
- [x] `SECURITY.md` + `supported_product_line: 0.x`; examples regenerated without local Windows paths
- [x] Branch-protection / ruleset docs in `AUTHDIFF-GATE.md`
- [ ] Publish `authdiff` 0.3.0 to PyPI + tag `v0.3.0` (needs maintainer release)
- [x] Mark GitHub Release `v1.0.0` prerelease/superseded

### Days 4–14 · Pins (0.3.0)

- [x] Lock records include `launcher`, `args_digest`, `url_host`, `script_digest`
- [x] Same-name package/launcher swap classified as `replacement`
- [x] `lock --snapshot` / `--resolve` hint; schema-validate locks on load
- [x] Hostile lock tests (malformed / hollow / reorder)

### Days 15–21 · Approval (0.3.0)

- [x] Delete homemade owner∩approver matching; GitHub-native approval model
- [x] Action loads CODEOWNERS from base ref (`--codeowners`)
- [x] Ruleset / stale-review docs in `AUTHDIFF-GATE.md`

### Days 22–30 · Habit + shrink (0.3.0)

- [x] `lock --home` + Claude PreToolUse hook template
- [x] README leads with `doctor`
- [x] Kill list: archive/atlas/pilots/kit + unused schemas + research CLI
- [ ] Five outside repos + 100 blind labels *(operator / outreach)*

### Days 1–5 · One release truth

- [x] Single version manifest + build parity checks
- [x] Rules catalogue synced to pack 1.6 / 001–022
- [x] Consumer-gate example lock-first + SHA pin guidance
- [x] Canonical skill at `skills/authdiff-auditor`
- [x] CI fails on version/schema drift (`authdiff-dev build`)

### Days 6–12 · First use

- [x] `authdiff demo` first command; bare CLI → `scan .`
- [x] Advanced + review commands hidden from brief `--help`
- [x] Six-command public mental model (`CORE_PUBLIC_COMMANDS`)
- [x] `authdiff-dev` maintainer split
- [x] Demo fixture bundled in the wheel (`authdiff/data/demo-vulnerable`)
- [ ] Publish `authdiff` to PyPI (workflow ready; needs trusted publisher)
- [ ] Validate install in a clean Python environment (operator checklist)

### Days 13–20 · Authority gate

- [x] Action `locked` default **true** (current pin `@v0.3.0`)
- [x] Trusted base-ref policy loading
- [x] Addition / expansion / reduction / replacement / representation / mixed tests
- [x] Gated findings require evidence ids (`is_gate_finding`)
- [x] `ci init` writes CODEOWNERS + lock-first workflow
- [x] Branch-protection / least-privilege docs in `AUTHDIFF-GATE.md`
- [x] PR comment fields: Change, Authority delta, Evidence, Risk, Confidence, Coverage, Required
- [x] Approval records on `AUTHORITY.lock` (`lock --approval`)
- [x] Distinguish `NO_NEW_AUTHORITY` vs `AUTHORITY_NOT_ESTABLISHED`

### Days 21–30 · External validation

- [x] Evaluation protocol published ([`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md))
- [x] One external pilot (`docs/pilots/` — playwright-mcp)
- [ ] Recruit ≥5 external maintainers *(outreach — not code)*
- [ ] Re-run pilot matrix on ≥5 repos *(operator)*

---

## 90-day maturity — status

### Days 31–60 · Coverage that moves the authority boundary

- [x] Per-adapter maturity specs ([`adapters/`](adapters/))
- [x] Authority layer honesty on every scan (`DECLARED`/`CONFIGURED`/`EFFECTIVE`/`VERIFIED`)
- [x] Hooks lifecycle + host-identity hints
- [x] MCP client / skills / CI fixture coverage (rule quality pack)
- [ ] Promote selected PARTIAL adapters to SUPPORTED only with fixture evidence
- [ ] Host-effective permission probes (authorized / opt-in only)

### Days 61–90 · Trust + distribution

- [x] Authority SBOM export (`authority-sbom.json`)
- [x] Agent Authority Manifest schema + draft/verify
- [x] Provenance block on `findings.json`
- [x] Sigstore release workflow present
- [x] Precision ledger scaffold ([`atlas/`](atlas/))
- [ ] PyPI publication + signed release checksums on a public tag
- [ ] Labeled holdout precision ≥ 90% for HIGH/CRITICAL
- [ ] Second CI provider only if customer demand requires it

**90-day milestone:** unrelated teams install authdiff, understand the output,
adopt the lockfile workflow, and keep using it across real PRs.

---

## Success metrics

| Dimension | Metric | Target |
| --- | --- | --- |
| Activation | First useful authority map | &lt; 2 minutes |
| Activation | CI integration | &lt; 10 minutes |
| UX | Default PR comment | ≤ 12 lines |
| Evidence | Gated findings with evidence refs | 100% |
| Trust | Unsupported `CONFIRMED` claims | 0 |
| Safety | Target code executed in passive scan | 0 |
| Quality | High-severity rule precision (independent) | &gt; 90% |
| Coverage | Unsupported surfaces explicitly reported | 100% |
| Coverage | Known authority-bearing changes detected by supported adapters | Establish baseline, then improve |
| Approval | Authority diffs causing least-privilege change / reject / explicit accept | Track qualitatively then quantitatively |
| Adoption | Independent orgs using CI | 10+ by day 90 |
| Retention | Repos still gated after 30 days | &gt; 70% |

---

## Architecture (visible surface)

1. **Core engine** — parsers, normalized authority model, rules, evidence  
2. **Authority engine** — lock, fingerprints, diff classes, policy  
3. **Interfaces** — CLI, GitHub Action, optional coding-agent skill  
4. **Human control** — CODEOWNERS, review, suppressions, risk acceptance  
5. **Contracts** — schemas, adapter maturity, rule versions, reproducibility  

No database, hosted service, MCP audit server, or web frontend in the committed
architecture until local CLI + CI workflows are insufficient for real users.

---

## Related

- [`PRODUCT.md`](PRODUCT.md) — frozen product contract  
- [`TRUST-AND-SAFETY.md`](TRUST-AND-SAFETY.md) — audit-process requirements  
- [`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md) — external pilots  
- [`AGENT-AUTHORITY-MANIFEST.md`](AGENT-AUTHORITY-MANIFEST.md) — manifest / SBOM  
- [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) — lock semantics  
- [`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md) — adapter honesty  
