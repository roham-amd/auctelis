# auctelis tooling

**Product CLI (`auctelis`):** `init --owner` → `check` → `lock --update` → `gate` / `diff` / `why` / `demo`.

**Maintainer CLI (`auctelis-dev`):** `scan`, `annotate`, `build`, `lint`, `deps`, `corpus`, `validate`, `inventory`, … — not the product gate.

Public `scan` / `vet` / `explain` / `watch` / `allow` / `hook` / `doctor` CLIs were **removed**.

**Full command reference:** [`../docs/CLI-REFERENCE.md`](../docs/CLI-REFERENCE.md)  
**Reach definition:** [`../docs/REACH.md`](../docs/REACH.md)  
**Docs index:** [`../docs/DOCUMENTATION-INDEX.md`](../docs/DOCUMENTATION-INDEX.md)

Package: `auctelis` **0.9.1** · Product: auctelis **0.9.1** (install pin: `@v0.9.1` — see [`INSTALL.md`](../docs/INSTALL.md))

---

## Stack (Python 3.12+)

| Responsibility | Choice |
| --- | --- |
| Runtime | CPython ≥3.12 (`.python-version` = `3.12`; CI pin `3.12.16`) |
| Project / venv / lock | **uv** + `pyproject.toml` + `uv.lock` |
| Dev deps | PEP 735 `[dependency-groups]` |
| Lint / format | Ruff |
| Types | mypy |
| Tests | Pytest (+ pytest-cov) |
| Vuln scan | pip-audit |
| CI | GitHub Actions + `uv sync --locked` |
| Optional container | Deferred — not the Authority Diff install |

Do **not** add Poetry, pip-tools, Pipenv, or a separate venv manager.

---

## Install

**User tool (recommended):**

```bash
uv tool install --python 3.12 \
  git+https://github.com/roham-amd/auctelis.git@v0.9.1#subdirectory=tools
# PyPI coming — git tag until the index returns the package.
auctelis init --owner security             # policy + workflow + CODEOWNERS + lock
auctelis check                             # repo authority vs AUTHORITY.lock
auctelis lock --update                     # seal AUTHORITY.lock (empty baseline OK)
auctelis diff --base origin/main           # local PR Authority Diff
auctelis why <name>                        # exact config path
auctelis demo                              # optional
```

Details: [`../docs/INSTALL.md`](../docs/INSTALL.md).

**Local development:**

```bash
cd tools
uv sync --locked
uv run auctelis --help
uv run auctelis check .
uv run auctelis-dev lint --check-format   # maintainer
```

`.python-version` selects the **minor** interpreter (`3.12`). Patch pins belong in CI (`uv python install 3.12.16`).

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

### Product (`auctelis`)

```bash
uv run auctelis check [PATH] [--json]
uv run auctelis lock [PATH] [--check] [--update] [--accept-gated]
uv run auctelis ci init --apply --owner @TEAM [PATH] [--force] [--advisory]
uv run auctelis gate [PATH] --base-lock PATH
uv run auctelis diff --base REF [--repo PATH]
uv run auctelis diff lock <base.lock> <head.lock>
uv run auctelis why NAME [PATH]
uv run auctelis demo [-o DIR]
```

### Maintainer (`auctelis-dev`)

```bash
uv run auctelis-dev scan PATH [-o DIR] [--fail-on never|high|any]
uv run auctelis-dev annotate FINDINGS.json --format github|text|pr-comment
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
| `authority_lock.py` / `lock_io.py` | AUTHORITY.lock v1 write / check / diff / load |
| `authority_card.py` | One-line authority cards for PR comment |
| `gate.py` | Base-lock growth labels + CODEOWNERS / ruleset check |
| `security/` | Maintainer Guard engine: capabilities, rules, scan, baseline, report |
| `security/rules.py` | Deterministic rules AUCTELIS-RULE-001…022 (pack 1.6) |
| `inventory/` | Bounded I/O, adapter registry, collector, coverage |
| `inventory/adapters/` | Skills, MCP, hooks, plugins, subagents, automations, A2A, workflows |
| `export/` | SARIF, annotations, PR comment, agent digest |
| `validate_report.py` / `semantic.py` | Schema + semantic validation |
| `corpus/` | Tooling corpus runner |
| `build.py` | Consistency checks (schemas, versions, links, pins) |
| `versioning.py` | Product/package version resolution |
| `deps.py` / `pins.py` / `lint.py` | Engineering helpers |
| `jsonio.py` / `textutil.py` | Shared I/O and escaping |

Library entry points: package docstring and [`../docs/CLI-REFERENCE.md`](../docs/CLI-REFERENCE.md).

---

## Inventory adapters (maturity)

Adapters register in `inventory/adapters/registry.py`. Maturity appears on each component and in `coverage.adapter_matrix`.

| Family | Typical maturity | Notes |
| --- | --- | --- |
| Skills (`SKILL.md`) | SUPPORTED | Frontmatter + priority hints |
| Instruction rules | SUPPORTED | AGENTS.md / rule packs |
| MCP client config | PARTIAL | mcpServers registrations |
| MCP server source | PARTIAL | Heuristic source markers |
| Hooks | PARTIAL | hooks.json / hooks dirs (inventory only) |
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
