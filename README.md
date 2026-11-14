# Auctelis

**Package-lock for agent authority**

> See what your agents can reach, and what changed since you last said OK.

Auctelis inventories the MCP servers, skills, hooks, commands, and CI steps your
agents can use, seals the state you approved in `AUTHORITY.lock`, and prints one
line when that reach changes — at session start or in a PR comment. GitHub stays
the approval system (CODEOWNERS / rulesets). Deterministic tooling is the source
of truth; an agent can explain it, never approve it.

It is **not** a certification, runtime sandbox, or marketplace badge. Contract:
[`docs/PRODUCT.md`](docs/PRODUCT.md).

---

## First five minutes (Authority Watch)

```bash
# Git tag is the supported install until the PyPI package returns 200.
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.4.0#subdirectory=tools"

auctelis watch              # one screen: current declared reach vs your seal
auctelis watch --seal       # human baseline in ~/.auctelis/AUTHORITY.lock
auctelis watch --arm        # session + tool hooks for Cursor and Claude Code
auctelis hook status        # wired / not firing
```

The first screen is a delta, not a findings wall:

```text
+ mcp "linear" → mcp.linear.app · network · tools · unpinned · publisher NOT VERIFIED
```

After the seal, a new MCP server prints that one line in your next Cursor or
Claude session. An unchanged host stays quiet. A human reseals or reverts.

**Verdicts:** `PASS` | `NEEDS_REVIEW` | `BASELINE_ADOPTED` | `FAIL_CLOSED`.
**Labels:** `GROWTH` | `REDUCTION` | `NONE` (what the lock delta is, not a verdict).

Agents must export `AUCTELIS_AGENT=1`; `watch --seal`, `watch --arm`,
`hook install`, `lock`, and `ci init` are refused for agents.

---

## Team upsell (PR Authority Diff)

Lockless-first — one Action step, no baseline ceremony:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
# Prefer pinning the Action to a commit SHA.
# The Action ships the matching tools/ tree; do not uv-sync a PR-controlled one.
- uses: roham-amd/auctelis/.github/actions/auctelis-gate@v0.4.0
  with:
    path: .
    trusted-policy: "true"
    authority-diff: "true"
    locked: "false"          # post the diff; no lock required
    strict-ruleset: "true"   # UNVERIFIED protection fails growth
```

The comment is one verdict plus at most three `old → new` lines (host, launcher,
env keys). Finding IDs stay out of the review UI.

Approved-state upgrade: commit `AUTHORITY.lock`, set `locked: true`, then
`auctelis ci init --owner @team` for CODEOWNERS + workflow.

Full example: [`docs/auctelis-consumer-gate.example.yml`](docs/auctelis-consumer-gate.example.yml).
Gate docs: [`docs/AUCTELIS-GATE.md`](docs/AUCTELIS-GATE.md).

---

## Core commands

| Command | Purpose |
| --- | --- |
| `auctelis watch` | One-screen declared authority delta (front door) |
| `auctelis watch --seal` | Seal the human baseline (`lock --home` still works) |
| `auctelis watch --arm` / `hook install` | Session + tool hooks for Cursor and Claude Code |
| `auctelis hook status` | Wired / not firing |
| `auctelis gate` | Label growth vs `--base-lock`; strict ruleset default on |
| `auctelis ci init --owner @user` | Policy + lockless workflow + CODEOWNERS |
| `auctelis demo` | Packaged fixture (optional) |

`scan` / `check` / `vet` / `explain` / `harden` remain callable for existing
scripts but are hidden from the default first screen. The scanner is an
annotation layer, not the product.

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`AUCTELIS-GATE`](docs/AUCTELIS-GATE.md) · [`PLAYBOOK`](docs/PLAYBOOK.md) ·
[index](docs/DOCUMENTATION-INDEX.md).

Pilots / kill criterion: [`docs/pilots/`](docs/pilots/). Eval labels: [`eval/`](eval/).

---

## License

MIT — see [`LICENSE`](LICENSE).
