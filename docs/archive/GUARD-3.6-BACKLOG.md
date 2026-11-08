# authdiff / authdiff 3.6 implementation backlog

North-star remains **Authority Diff** on one facts engine
(`collector → Authority Snapshot → delta → new-only gate → sticky PR comment`).

Status key: `done` · `in_progress` · `next` · `deferred` · `frozen`

## Milestone W1 — Installable and honest

| ID | Deliverable | Status |
| --- | --- | --- |
| W1.1–W1.8 | Install crash, FP hotfixes, decision honesty, aliases | done |
| W1.9 | Publish PyPI (`authdiff`) via trusted publishing | next (workflow ready; tag `v3.6.1`) |
| W1.10 | Docker → `python:3.12.16-slim-trixie` | done |
| W1.11 | Target-policy blindfold + sticky comment + open parser | done (3.6.1) |

## Milestone W2–W3 — Facts + Authority Diff

| ID | Deliverable | Status |
| --- | --- | --- |
| W2.1–W2.2 | Claude settings + JSONC MCP | done |
| W3.1–W3.3 | Base-vs-head Action + advisory init | done |
| W3.4 | Authority Snapshot + new-only gating (no fall-through) | done (3.6.1) |
| W3.5 | Exact pin semantics, RULE-012 demotion, curl\|sh split | done (3.6.1) |
| W3.6 | Rules-file Unicode, Codex TOML, `~/.claude.json` doctor | done (3.6.1) |
| Product rename to **authdiff** | done (`authdiff` compat alias) |
| Physical archive `archive/methodology/` | done |

## Milestone W4 / 90-day

| ID | Deliverable | Status |
| --- | --- | --- |
| W4.1 | Atlas crawl harness (target N≥300) | done (seed; expand via seed JSON) |
| W4.2 | Benign corpus must not BLOCK | done |
| W4.3 | Attack-replay corpus | done (`examples/attack-replay/`) |
| D61 | Artifact-level vet (`authdiff artifact-vet`) | done (registry metadata) |
| D62 | Sandboxed tools/list snapshot | done (`authdiff snapshot`) |
| D63 | Sigstore + SBOM workflow | done (`.github/workflows/sigstore-release.yml`) |

## Radical alternatives

| ID | Deliverable | Status |
| --- | --- | --- |
| R1 | Authority broker `authdiff run` | done (MVP env scrub) |
| R2 | Attack-replay Metasploitable set | done |
| R3 | AUTHORITY schemas + `lsp-validate` | done (full LSP deferred) |

See [`RADICAL-ALTERNATIVES.md`](RADICAL-ALTERNATIVES.md).
