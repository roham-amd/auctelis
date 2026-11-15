# Auctelis

**The authority lockfile and PR gate for what AI agents can reach.**

> See the reach; approve every change.

Auctelis inventories MCP servers, skills, hooks, instructions, and commands in a
repository, seals what you approved in `AUTHORITY.lock`, and posts one Authority
Diff on every PR. It is a **consent ledger for agent reach**, not a sandbox,
certification, or marketplace badge.

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Reach: [`docs/REACH.md`](docs/REACH.md)

---

## First ten minutes

```bash
# Git tag until PyPI returns 200 for 0.8.1+.
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.8.1#subdirectory=tools"

cd your-repo
auctelis init --owner @security   # policy + workflow + CODEOWNERS + lock
# commit, open PR → BASELINE_ADOPTED; later growth needs CODEOWNERS

auctelis check                    # repo authority vs AUTHORITY.lock
auctelis status                   # lock / workflow / CODEOWNERS / protection
auctelis diff --base origin/main  # local PR Authority Diff simulator
auctelis why linear               # exact config path for one name
```

On a PR, the Action posts the base→head Authority Diff. First lock is
`BASELINE_ADOPTED` (not `PASS`). Growth fails until a CODEOWNER reviews the lock.
An empty (0-record) base lock is **empty-baseline growth** — CODEOWNERS review,
not a permanent `FAIL_CLOSED`. Locally, `auctelis check` is the pre-push preflight.

```text
+ mcp "linear" → mcp.linear.app · network · tools · unpinned · publisher NOT VERIFIED
Needs approval from: @security
```

**Labels:** `GROWTH` | `REDUCTION` | `NONE`  
**Verdicts:** `LOCKED` | `BASELINE_NEEDED` | `NEEDS_REVIEW` | `BASELINE_ADOPTED`

Agents must export `AUCTELIS_AGENT=1`; `lock`, `init`, and `ci init` are refused for agents
(`AUCTELIS_AGENT` is a speed bump, not a security control).

---

## Core commands

| Command | Purpose |
| --- | --- |
| `auctelis init --owner @team` | One-command setup (preferred) |
| `auctelis` / `check` | Repo authority vs `AUTHORITY.lock` (front door) |
| `auctelis status` | Lock / workflow / CODEOWNERS / protection |
| `auctelis lock --update` | Write / refresh the committed lock |
| `auctelis ci init --apply --owner @team` | Same as init (legacy alias path) |
| `auctelis gate --base-lock base.lock` | PR Authority Diff + CODEOWNERS gate |
| `auctelis diff --base <ref>` | Local PR Authority Diff simulator |
| `auctelis why <name>` | Exact config path / fields for one record |
| `auctelis demo` | Packaged fixture (optional) |

Host tripwires and the public scanner CLIs were removed in 0.8.0. Annotation
helpers for CI live on `auctelis-dev` (`scan` / `annotate`). The product gate is
**lock-only** — rule findings are research, not a gate input.

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`REACH`](docs/REACH.md) · [`AUTHORITY-LOCK`](docs/AUTHORITY-LOCK.md) ·
[`AUCTELIS-GATE`](docs/AUCTELIS-GATE.md) · [index](docs/DOCUMENTATION-INDEX.md).

Pilots: [`docs/pilots/`](docs/pilots/).

---

## License

MIT — see [`LICENSE`](LICENSE).
