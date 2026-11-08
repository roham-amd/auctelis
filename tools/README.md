# authdiff tooling (`authdiff`)

Agent Authority Change Control CLI: demo, doctor, pre-install vet, repo scan,
`AUTHORITY.lock`, CI gate helpers, plus maintainer corpus / AgentSecBench harness.

**Full command reference:** [`../docs/CLI-REFERENCE.md`](../docs/CLI-REFERENCE.md)  
**Scan guide:** [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md)  
**Rule catalog:** [`../docs/SECURITY-RULES.md`](../docs/SECURITY-RULES.md)  
**Docs index:** [`../docs/DOCUMENTATION-INDEX.md`](../docs/DOCUMENTATION-INDEX.md)

Package: `authdiff` **1.0.0** · Product: authdiff **1.0.0**

---

## Stack (Python 3.12+)

| Responsibility | Choice |
| --- | --- |
| Runtime | CPython ≥3.12 (`.python-version` = `3.12`; CI/Docker pin `3.12.16`) |
| Project / venv / lock | **uv** + `pyproject.toml` + `uv.lock` |
| Dev deps | PEP 735 `[dependency-groups]` |
| Lint / format | Ruff |
| Types | mypy |
| Tests | Pytest (+ pytest-cov) |
| Vuln scan | pip-audit |
| CI | GitHub Actions + `uv sync --locked` |
| Deploy | Docker (`uv sync --locked --no-dev`) |

Do **not** add Poetry, pip-tools, Pipenv, or a separate venv manager.

---

## Install

**User tool (recommended):**

```bash
uv tool install --python 3.12 \
  git+https://github.com/roham-amd/authdiff.git@v1.0.0#subdirectory=tools
# PyPI not published yet — git tag/SHA only.
authdiff demo
authdiff doctor
authdiff open github.com/org/some-skill
authdiff scan /path/to/target-repo   # bare `authdiff` also defaults to scan .
authdiff lock
```

Details: [`../docs/INSTALL.md`](../docs/INSTALL.md).

**Local development:**

```bash
# https://docs.astral.sh/uv/getting-started/installation/
cd tools
uv sync --locked          # creates .venv from uv.lock
uv run authdiff --help
uv run authdiff doctor
uv run authdiff scan /path/to/target-repo
```

Primary path: **`doctor` / `vet` / `scan`**.  
`authdiff audit --profile …` remains for agent handoff packages.
`authdiff annotate` emits PR annotations; `authdiff pilots run` exercises curated targets.

`.python-version` selects the **minor** interpreter (`3.12`). Patch pins belong in CI (`uv python install 3.12.16`) and the Docker base (`python:3.12.16-slim-trixie@sha256:…`).

### Dependency layout

| Requirement | Location / command |
| --- | --- |
| Runtime deps | `pyproject.toml` `[project].dependencies` (constraints via `uv add`) |
| Dev deps | `pyproject.toml` `[dependency-groups] dev` (`uv add --dev …`) |
| Exact versions + hashes | `uv.lock` (commit it) |
| Install | `uv sync --locked` |
| Updates | `uv add` / `uv lock --upgrade` / `authdiff deps upgrade` |
| Git | Commit `pyproject.toml`, `uv.lock`, `.python-version` — ignore `.venv/` |

```bash
uv add jsonschema
uv add --dev ruff
uv lock --upgrade
uv sync --locked
uv tree
authdiff deps outdated
```

### Docker

Root [`Dockerfile`](../Dockerfile) uses digest-pinned `python:3.12.16-slim-trixie` and `ghcr.io/astral-sh/uv`, then `uv sync --locked --no-dev`.

```bash
docker compose build
TARGET=/path/to/repo docker compose run --rm authdiff \
  scan /work -o /work/authdiff-out
```

Operator guide: [`../docs/archive/docker-agent-audit.md`](../docs/archive/docker-agent-audit.md).

### Pre-commit (optional)

```bash
uvx pre-commit install
uvx pre-commit run --all-files
```

Config: [`.pre-commit-config.yaml`](../.pre-commit-config.yaml).

### Quality gates

```bash
uv run --locked authdiff lint --check-format
uv run --locked mypy authdiff
uv run --locked pip-audit
uv run --locked pytest -q ../tests
uv run --locked authdiff-dev build all
uv run --locked authdiff corpus run
uv run --locked authdiff benchmark run
```

**Dependabot** (`.github/dependabot.yml`): weekly `uv`, `docker` (tag@digest), and SHA-pinned `github-actions`.

---

## Commands (summary)

```bash
# Primary product surface
uv run authdiff doctor [--home DIR] [-o DIR] [--agent]
uv run authdiff vet SOURCE [-o DIR] [--agent]
uv run authdiff init-gate [PATH] [--force]
uv run authdiff scan PATH [-o DIR] [--baseline B] [--save-baseline B] [--fail-on never|high|any] [--agent]
uv run authdiff harden [--findings PATH]
uv run authdiff init-manifest [PATH] [--force]
uv run authdiff verify-manifest [PATH] [-o REPORT.json]
uv run authdiff explain F-001 -o DIR [--agent]
uv run authdiff annotate FINDINGS.json --format github|text|pr-comment
uv run authdiff baseline save|show …

# Agent handoff / discovery
uv run authdiff audit PATH --profile quick|standard|deployment
uv run authdiff preflight PATH
uv run authdiff inventory PATH

# Validation / interop
uv run authdiff validate report|graph|claim PATH
uv run authdiff graph paths PATH
uv run authdiff diff report|graph|risk …
uv run authdiff export sarif REPORT.json
uv run authdiff verify digest|manifest …

# Engineering
uv run authdiff-dev build all|schemas|prompts [--write]
uv run authdiff corpus run
uv run authdiff benchmark run
uv run authdiff deps outdated|upgrade
uv run authdiff lint [--fix] [--format] [--check-format]
```

---

## Code layout (`tools/authdiff`)

| Module / package | Responsibility |
| --- | --- |
| `cli/` | argparse construction + command dispatch |
| `security/` | Guard engine: capabilities, rules, scan, baseline, report |
| `security/rules.py` | Deterministic rules AUTHDIFF-RULE-001…022 (pack 1.6) |
| `authority_lock.py` | AUTHORITY.lock v2 write / check / diff |
| `security/scan.py` | Artifact writer + policy fail-on + PR comment |
| `security/decision.py` | BLOCK / REVIEW / NO-GATED-FINDINGS |
| `harden.py` / `authority_manifest.py` | Dry-run patches + AUTHORITY.yml |
| `doctor.py` / `vet.py` | Host map + pre-install verdict |
| `inventory/` | Bounded I/O, adapter registry, collector, coverage |
| `inventory/adapters/` | Skills, MCP, hooks, plugins, subagents, automations, A2A, workflows |
| `audit.py` / `preflight.py` | Profile orchestration + graph seed + audit-context |
| `export/` | SARIF, annotations, PR comment, agent digest |
| `validate_report.py` / `semantic.py` | Schema + semantic validation |
| `graph/analysis.py` | Graph path helpers |
| `benchmark/` / `corpus/` | AgentSecBench + tooling corpus runners |
| `supply_chain/` | Digest / manifest helpers |
| `build.py` / `prompt_build.py` | Consistency checks + monolith |
| `versioning.py` | Product/package version resolution |
| `deps.py` / `pins.py` / `lint.py` | Engineering helpers |
| `jsonio.py` | Shared JSON/text I/O |

Library entry points are documented in the package docstring and [`../docs/CLI-REFERENCE.md`](../docs/CLI-REFERENCE.md).

---

## Inventory adapters (maturity)

Adapters register in `inventory/adapters/registry.py`. Maturity appears on each component and in `coverage.adapter_matrix`.

| Family | Typical maturity | Notes |
| --- | --- | --- |
| Skills (`SKILL.md`) | SUPPORTED | Frontmatter + priority hints |
| Instruction rules | SUPPORTED | AGENTS.md / rule packs |
| MCP client config | PARTIAL | mcpServers registrations |
| MCP server source | PARTIAL | Heuristic source markers |
| Hooks | PARTIAL | hooks.json / hooks dirs |
| Plugins / subagents / automations | PARTIAL | Host-component heuristics |
| A2A agent cards | PARTIAL | agent-card.json style |
| GitHub workflows | PARTIAL | `.github/workflows` |
| Host effective permissions | MANUAL_ONLY | Requires host evidence |
| Runtime behavior | UNSUPPORTED in passive mode | Separate authorization |

Incomplete coverage must never be treated as a clean security result.

---

## Related product docs

- [`../docs/AUTHDIFF-GATE.md`](../docs/AUTHDIFF-GATE.md)
- [`../docs/archive/AESA-3.0-PRODUCT-SPEC.md`](../docs/archive/AESA-3.0-PRODUCT-SPEC.md) (historical)
- [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md)
- [`../docs/archive/toolchain-threat-model.md`](../docs/archive/toolchain-threat-model.md)
