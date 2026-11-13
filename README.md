# Auctelis

**The authority lockfile and PR security gate for AI agents**

> Know what authority your AI agents have, what changes when integrations are introduced, and whether those changes have been approved.

`auctelis` inventories AI-agent authority (skills, MCP, hooks, plugins, subagents,
CI, host configs), locks the approved state in `AUTHORITY.lock`, and fails CI when
authority expands without review.

It is **not** a certification, marketplace badge, runtime sandbox, or substitute
for organizational risk acceptance. Deterministic tooling is the source of truth;
an AI agent is an optional explainer. Product contract:
[`docs/PRODUCT.md`](docs/PRODUCT.md).

---

## Job to be done

> Before I install, merge, deploy, or upgrade an AI-agent integration, tell me
> what new authority it introduces, who receives it, and whether that change
> has been approved.

The valuable artifact is the **PR Authority Diff comment** (≤12 lines) plus
committed [`AUTHORITY.lock`](docs/AUTHORITY-LOCK.md) — not a long report.

---

## First useful minute

```bash
# Working install (git tag — PyPI is not published yet):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.3.3#subdirectory=tools" auctelis doctor

# Later, once the package is on the index:
# uvx --from auctelis auctelis doctor
```

Persistent install (if continuing):

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.3.3#subdirectory=tools"

auctelis doctor                  # your host authority map (the aha)
auctelis doctor --since-lock     # one-screen delta vs ~/.auctelis/AUTHORITY.lock
auctelis lock --home             # seal ~/.auctelis/AUTHORITY.lock
auctelis                         # bare CLI → doctor, or scan . when lock/policy exists
auctelis demo                    # canned evil fixture (optional)
auctelis vet github.com/org/some-skill
auctelis lock                    # write repo AUTHORITY.lock (--accept-gated if needed)
auctelis gate --base-lock path/to/base.lock  # label growth; CODEOWNERS/rulesets enforce
auctelis ci init --owner @you    # .auctelis.yml + workflow + CODEOWNERS
auctelis check --locked          # fail on lock drift
```

Hook (Claude Code): `tools/auctelis/templates/claude-pretool-authority-hook.sh`
(Python JSON parser; thin shell wrapper).

Public path: **doctor → lock → scan/gate → ci init** (demo / vet optional).

Artifacts default to **`./auctelis-out`**. Target `.auctelis.yml` suppressions are **ignored**
unless you pass `--policy` or `--trust-target-policy`. Use `--agent` for a compact
fenced JSON digest. Use `--full` for the long report. Agents should export
`AUCTELIS_AGENT=1` so mutating lock/policy paths are refused.

**Install honesty:** auctelis is **not on PyPI yet**. Install from a git tag (or pin a
commit SHA). Prefer an immutable Action commit SHA in high-assurance repos.

### Core commands

| Command | Purpose |
| --- | --- |
| `auctelis doctor` | Host authority map (lead with this) |
| `auctelis lock` / `lock --home` | Write repo or `~/.auctelis` lock (`--snapshot`, `--accept-gated`) |
| `auctelis` / `scan` / `check` | Repo authority scan (add `--locked`) |
| `auctelis gate` | Label growth vs `--base-lock`; require CODEOWNERS + ruleset |
| `auctelis ci init --owner @user` | `.auctelis.yml` + lock-first workflow + CODEOWNERS |
| `auctelis vet` | Pre-install annotations (safe shallow clone; no REJECT from hints) |
| `auctelis demo` | Packaged evil fixture (optional aha) |

Review / advanced / maintainer tiers: [`docs/PRODUCT.md`](docs/PRODUCT.md) ·
[`docs/CLI-REFERENCE.md`](docs/CLI-REFERENCE.md).

Docs: [`docs/DOCUMENTATION-INDEX.md`](docs/DOCUMENTATION-INDEX.md) ·
[`docs/AUTHORITY-LOCK.md`](docs/AUTHORITY-LOCK.md) ·
[`docs/COVERAGE-MATRIX.md`](docs/COVERAGE-MATRIX.md) ·
[`docs/ROADMAP.md`](docs/ROADMAP.md) ·
demo [`examples/demo-vulnerable/`](examples/demo-vulnerable/)

Research/archive trees were removed in 0.3.0; see [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## CI gate

Single recipe (git-tag install + Action). Full example:
[`docs/auctelis-consumer-gate.example.yml`](docs/auctelis-consumer-gate.example.yml).

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
# PyPI not published yet — install from the pinned kit tag, then use Action-bundled tools:
- run: >
    pip install
    "git+https://github.com/roham-amd/auctelis.git@v0.3.3#subdirectory=tools"
# Prefer: uses: roham-amd/auctelis/.github/actions/auctelis-gate@<commit-sha>
- uses: roham-amd/auctelis/.github/actions/auctelis-gate@v0.3.3
  with:
    path: .
    trusted-policy: "true"
    authority-diff: "true"
    locked: "true"    # lock-first: AUTHORITY.lock must be committed
    install-tools-from: path
```

Pin the Action by **immutable commit SHA** in high-assurance repos
(see [`docs/AUCTELIS-GATE.md`](docs/AUCTELIS-GATE.md)). Tag pins are convenient but mutable.

With `authority-diff=true`, the Action scans the PR **base** ref and diffs it
against **head**. With `trusted-policy=true`, policy loads from the base ref.
`locked` **defaults to true** — AUTHORITY.lock drift fails the check.

---

## What auctelis evaluates

Skills, MCP servers, hooks, plugins, subagents, rules, automations, CI
workflows, and host agent configuration. Finding classes: only
`SECURITY_FINDING` and `EXPOSURE` can fail CI. `CAPABILITY` is inventory.
Decisions are `BLOCK` / `REVIEW` / `NO-GATED-FINDINGS` — never a numeric trust
score. Unparsed configs and `MANUAL_ONLY` surfaces are reported as coverage
gaps ([`docs/COVERAGE-MATRIX.md`](docs/COVERAGE-MATRIX.md)).

Authority layers (never conflate): **Declared → Configured → Effective → Verified**.
A passive scan establishes Declared/Configured only
([`docs/TRUST-AND-SAFETY.md`](docs/TRUST-AND-SAFETY.md)).

---

## Core principles

- Prefer `NOT VERIFIED` over unsupported assurance.
- Never execute, install, or contact target-controlled services during a passive audit
  (except explicit opt-in commands: `snapshot`, `run`).
- Never request or expose production secrets.
- The AI auditor explains; it is never the evidence source of truth.
- Policy that the PR author can edit is not a gate — use `trusted-policy`.
- Gated findings always cite evidence ids; `NAME_MARKER` never gates alone.

---

## License

MIT — see [`LICENSE`](LICENSE).
