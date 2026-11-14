# auctelis tooling (`auctelis`)

Authority Watch CLI: `watch` → `--seal` → `--arm` → `why` → `hook status`.
Repo `AUTHORITY.lock` + optional PR Action/`gate` are the team upsell. `scan` /
`vet` are hidden annotation layers.

**Full command reference:** [`../docs/CLI-REFERENCE.md`](../docs/CLI-REFERENCE.md)  
**Reach definition:** [`../docs/REACH.md`](../docs/REACH.md)  
**Docs index:** [`../docs/DOCUMENTATION-INDEX.md`](../docs/DOCUMENTATION-INDEX.md)

Package: `auctelis` **0.5.0** · Product: auctelis **0.5.0**

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
  git+https://github.com/roham-amd/auctelis.git@v0.5.0#subdirectory=tools
# PyPI not published yet — git tag/SHA only.
auctelis                    # highlights + inventory, or sealed delta
auctelis watch --seal       # human baseline in ~/.auctelis/AUTHORITY.lock
auctelis watch --arm        # session + tripwire hooks
auctelis hook status        # wired / not yet observed / firing
auctelis why <name>         # exact config path
auctelis demo               # optional
```

Details: [`../docs/INSTALL.md`](../docs/INSTALL.md).

**Local development:**

```bash
# https://docs.astral.sh/uv/getting-started/installation/
cd tools
uv sync --locked          # creates .venv from uv.lock
uv run auctelis --help
uv run auctelis watch --home /tmp/auctelis-home
uv run auctelis scan /path/to/target-repo   # hidden annotation layer
```

Primary path: **`watch` / `--seal` / `--arm` / `why` / `hook status`**.
`gate` / `ci init` / `scan` / `vet` are optional or hidden.

`.python-version` selects the **minor** interpreter (`3.12`). Patch pins belong in CI (`uv python install 3.12.16`) and the Docker base (`python:3.12.16-slim-trixie@sha256:…`).

### Dependency layout

| Requirement | Location / command |
| --- | --- |
| Runtime deps | `pyproject.toml` `[project].dependencies` (constraints via `uv add`) |
| Dev deps | `pyproject.toml` `[dependency-groups] dev` (`uv add --dev …`) |
| Exact versions + hashes | `uv.lock` (commit it) |
| Install | `uv sync --locked` |
| Updates | `uv add` / `uv lock --upgrade` / `auctelis-dev deps upgrade` |
| Git | Commit `pyproject.toml`, `uv.lock`, `.python-version` — ignore `.venv/` |

```bash
uv add jsonschema
uv add --dev ruff
uv lock --upgrade
uv sync --locked
uv tree
auctelis-dev deps outdated
```

### Docker

Root [`Dockerfile`](../Dockerfile) uses digest-pinned `python:3.12.16-slim-trixie` and `ghcr.io/astral-sh/uv`, then `uv sync --locked --no-dev`.

```bash
docker compose build
TARGET=/path/to/repo docker compose run --rm auctelis \
  scan /work -o /work/auctelis-out
```

Operator guide: [`../docs/INSTALL.md`](../docs/INSTALL.md).

### Pre-commit (optional)

```bash
uvx pre-commit install
uvx pre-commit run --all-files
```

Config: [`.pre-commit-config.yaml`](../.pre-commit-config.yaml).

### Quality gates

```bash
uv run --locked auctelis-dev lint --check-format
uv run --locked mypy auctelis
uv run --locked pip-audit
uv run --locked pytest -q ../tests
uv run --locked auctelis-dev build all
uv run --locked auctelis-dev corpus run
```

**Dependabot** (`.github/dependabot.yml`): weekly `uv`, `docker` (tag@digest), and SHA-pinned `github-actions`.

---

## Commands (summary)

```bash
# Primary product surface
uv run auctelis watch [--home DIR] [--lock-file PATH] [--seal] [--arm] [--delta-only]
uv run auctelis hook install [--home DIR] [--no-cursor]
uv run auctelis hook status [--home DIR] [--json]
uv run auctelis ci init --owner @TEAM [PATH] [--force]
uv run auctelis gate [PATH] --base-lock PATH

# Hidden annotation layer (callable, not the first screen)
uv run auctelis scan PATH [-o DIR] [--baseline B] [--save-baseline B] [--fail-on never|high|any] [--agent]
uv run auctelis vet SOURCE [-o DIR] [--agent]
uv run auctelis lock [PATH] [--check] [--accept-gated] [--home]
uv run auctelis harden [--findings PATH]
uv run auctelis explain F-001 -o DIR [--agent]
uv run auctelis annotate FINDINGS.json --format github|text|pr-comment

# Maintainer (auctelis-dev)
uv run auctelis-dev validate report PATH
uv run auctelis-dev inventory PATH
uv run auctelis-dev export sarif REPORT.json
uv run auctelis-dev verify digest PATH
uv run auctelis-dev build all|schemas
uv run auctelis-dev corpus run
uv run auctelis-dev deps outdated|upgrade
uv run auctelis-dev lint [--fix] [--format] [--check-format]
```

---

## Code layout (`tools/auctelis`)

| Module / package | Responsibility |
| --- | --- |
| `cli/` | argparse construction + command dispatch |
| `security/` | Guard engine: capabilities, rules, scan, baseline, report |
| `security/rules.py` | Deterministic rules AUCTELIS-RULE-001…022 (pack 1.6) |
| `authority_lock.py` / `lock_io.py` | AUTHORITY.lock v1 write / check / diff / load |
| `authority_card.py` | One-line authority cards for watch / PR comment |
| `watch.py` / `host_scan.py` | Authority Watch screen + host discovery/staging |
| `hooks.py` / `templates/` | Cursor + Claude hook installation and status |
| `gate.py` | Base-lock growth labels + CODEOWNERS / ruleset check |
| `security/scan.py` | Artifact writer + policy fail-on + PR comment |
| `security/decision.py` | Internal BLOCK / REVIEW / NO-GATED-FINDINGS annotation |
| `harden.py` | Dry-run least-privilege patch proposals |
| `doctor.py` | Alias for the watch screen |
| `vet.py` | Hidden pre-install annotation layer |
| `inventory/` | Bounded I/O, adapter registry, collector, coverage |
| `inventory/adapters/` | Skills, MCP, hooks, plugins, subagents, automations, A2A, workflows |
| `preflight.py` | Graph seed + audit-context helpers |
| `export/` | SARIF, annotations, PR comment, agent digest |
| `validate_report.py` / `semantic.py` | Schema + semantic validation |
| `graph/analysis.py` | Graph path helpers |
| `corpus/` | Tooling corpus runner |
| `supply_chain/` | Digest helpers |
| `build.py` | Consistency checks (schemas, versions, links, pins) |
| `versioning.py` | Product/package version resolution |
| `deps.py` / `pins.py` / `lint.py` | Engineering helpers |
| `jsonio.py` | Shared JSON/text I/O |
| `textutil.py` | Markdown/terminal escaping shared by rules and exports |
| `broker.py` / `mcp_snapshot.py` / `process_env.py` | Advanced run/snapshot surfaces |

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

- [`../docs/AUCTELIS-GATE.md`](../docs/AUCTELIS-GATE.md)
- [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md)
- [`../docs/DOCUMENTATION-INDEX.md`](../docs/DOCUMENTATION-INDEX.md)
