# Auctelis

**The authority lockfile and PR review for what AI agents can reach.**

> See what a repo’s agent configs can reach, and what changed since you last said OK.

Auctelis inventories MCP servers, skills, hooks, instructions, and commands in a
repository, seals what you approved in `AUTHORITY.lock`, and posts one Authority
Diff on every PR. It is a **consent ledger for agent reach**, not a sandbox,
certification, or marketplace badge.

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Reach: [`docs/REACH.md`](docs/REACH.md)

---

## First ten minutes

```bash
# Git tag is the supported install until PyPI returns 200.
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.8.0#subdirectory=tools"

auctelis check                  # repo authority vs AUTHORITY.lock
auctelis lock --update          # seal the current tree into AUTHORITY.lock
auctelis ci init --apply --owner @security   # merge CODEOWNERS + verify ruleset
auctelis diff --base origin/main             # local PR Authority Diff simulator
auctelis why linear             # exact config path for one name
```

On a PR, the Action posts the base→head Authority Diff. First lock is
`BASELINE_ADOPTED` (not `PASS`). Growth fails until a CODEOWNER reviews the lock.
Locally, `auctelis check` is the pre-push preflight.

```text
+ mcp "linear" → mcp.linear.app · network · tools · unpinned · publisher NOT VERIFIED
```

**Labels:** `GROWTH` | `REDUCTION` | `NONE`  
**Verdicts:** `LOCKED` | `BASELINE_NEEDED` | `NEEDS_REVIEW` | `BASELINE_ADOPTED`

Agents must export `AUCTELIS_AGENT=1`; `lock` and `ci init` are refused for agents.

---

## Core commands

| Command | Purpose |
| --- | --- |
| `auctelis` / `check` | Repo authority vs `AUTHORITY.lock` (front door) |
| `auctelis lock --update` | Write / refresh the committed lock |
| `auctelis ci init --apply --owner @team` | Enforce workflow + CODEOWNERS + ruleset verify |
| `auctelis gate --base-lock base.lock` | PR Authority Diff + CODEOWNERS gate |
| `auctelis diff --base <ref>` | Local PR Authority Diff simulator |
| `auctelis why <name>` | Exact config path / fields for one record |
| `auctelis demo` | Packaged fixture (optional) |

`watch` / `allow` / `hook` / `doctor` remain callable for compatibility but are
archived from the product path. `scan` is a hidden annotation layer.

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`REACH`](docs/REACH.md) · [`AUTHORITY-LOCK`](docs/AUTHORITY-LOCK.md) ·
[`AUCTELIS-GATE`](docs/AUCTELIS-GATE.md) · [index](docs/DOCUMENTATION-INDEX.md).

Pilots: [`docs/pilots/`](docs/pilots/).

---

## License

MIT — see [`LICENSE`](LICENSE).
