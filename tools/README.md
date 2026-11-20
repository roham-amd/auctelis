# auctelis tooling

**Product CLI (`auctelis`):** `check` → `check --report` → `diff --base` →
lockless workflow or `init --owner --enforce` → `gate`.

**Maintainer CLI (`auctelis-dev`):** workspace member `tools/dev/auctelis_devtools`
(not in the product wheel). `scan`, `annotate`, `build`, `lint`, `deps`,
`corpus`, `validate`, `inventory`, … — not the product gate.

Public `scan` / `vet` / `explain` / `watch` / `allow` / `hook` / `doctor` CLIs were **removed**.

**Full command reference:** [`../docs/CLI-REFERENCE.md`](../docs/CLI-REFERENCE.md)  
**Reach definition:** [`../docs/REACH.md`](../docs/REACH.md)  
**Docs index:** [`../docs/DOCUMENTATION-INDEX.md`](../docs/DOCUMENTATION-INDEX.md)

Package: `auctelis` **0.17.1** · Product: auctelis **0.17.1** (tag `@v0.17.1`; see [`INSTALL.md`](../docs/INSTALL.md))

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
# Direct run (or `uv tool install --python 3.12 "git+https://github.com/roham-amd/auctelis.git@v0.17.1#subdirectory=tools"`):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.17.1#subdirectory=tools" auctelis check

auctelis check                         # repo authority vs AUTHORITY.lock
auctelis init --owner security         # policy + workflow + CODEOWNERS + lock
auctelis lock --update                 # seal AUTHORITY.lock (empty baseline OK)
auctelis diff --base origin/main       # local PR Authority Diff
auctelis why <name>                    # exact config path
auctelis demo                          # optional
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

**Dependabot** (`.github/dependabot.yml`): weekly `uv` and SHA-pinned `github-actions` (Docker install path removed).

---

## Commands (summary)

### Product (`auctelis`)

```bash
uv run auctelis check [PATH ...] [--json] [--pins] [--report DIR]
uv run auctelis lock [PATH] [--check] [--update] [--accept-gated]
uv run auctelis init [PATH] --lockless                    # one-file PR Watch
uv run auctelis init --owner TEAM [PATH] [--force] [--enforce]
uv run auctelis status [PATH] [--check]
uv run auctelis trust HOST [--list | --remove | --init]
uv run auctelis gate [PATH] --base-lock PATH
uv run auctelis diff --base REF [--repo PATH]
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

## Code layout

Product wheel (`tools/auctelis`):

| Module / package | Responsibility |
| --- | --- |
| `cli/` | argparse construction + command dispatch |
| `authority_lock.py` / `lock_io.py` | AUTHORITY.lock v1 write / check / diff / load |
| `authority_card.py` | One-line authority cards for PR comment |
| `gate.py` | Base-lock growth labels + CODEOWNERS / ruleset check |
| `security/` | Capabilities, evidence, gating, fingerprint, decision models |
| `inventory/` | Bounded I/O, adapter registry, collector, coverage |
| `inventory/adapters/` | Skills, MCP, hooks, plugins, subagents, automations, A2A, workflows |
| `export/` | PR comment, authority SBOM, reach report (HTML/MD/JSON) |
| `versioning.py` | Product/package version resolution |
| `jsonio.py` / `textutil.py` | Shared I/O, escaping, terminal hygiene |

Source-only maintainer package (`tools/dev/auctelis_devtools`, `auctelis-dev`):

| Module / package | Responsibility |
| --- | --- |
| `cli/` | Maintainer argparse extension + dev command handlers |
| `build.py` | Consistency checks (schemas, versions, links, pins, install docs) |
| `semantic.py` / `validate_report.py` | Schema + semantic validation |
| `export/sarif.py` / `export/agent_digest.py` | SARIF and agent digest exports |
| `deps.py` / `lint.py` | Engineering helpers (package-name normalization, dependency checks) |

Maintainer-only research lives in a separate package (`../tools/auctelis_research`):
rules/corpus/eval/attack-replay, the annotate helpers, and the graph analysis used
by corpus checks. It is not part of the product wheel.

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
