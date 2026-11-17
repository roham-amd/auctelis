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
# Working install today (PyPI name reserved; package publish follows pilots):
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.11.0#subdirectory=tools"
auctelis --version

cd your-repo
auctelis diff --base origin/main  # aha: local Authority Diff (no files written)

# Lockless (no init): paste templates/auctelis-diff.yml into .github/workflows/
# Or comment-only setup:
auctelis init --owner security    # advisory workflow + CODEOWNERS + lock
# PowerShell: omit @ — auctelis adds it. Use --enforce for locked gate.
# commit → PR → Authority Diff comment

auctelis check                    # repo authority vs AUTHORITY.lock
auctelis status --check           # OK for comment-only; nonzero if enforce unarmed
auctelis why linear               # exact config path for one name
```

On a PR, the Action diffs **tree-derived** base→head authority (committed lock
is drift-checked, never trusted as head) and always posts the Authority Diff
comment from that gate delta. Default `init` is **comment-only** (advisory);
pass `--enforce` for a required check. Auctelis **labels** growth and posts
the diff — it does **not** count PR approvals; GitHub CODEOWNERS/rulesets do
that when you enforce. Reach is tiered: inferred doc links stay comment-only;
execute/secrets/new MCP fail under `--enforce`. Body-only instruction edits
stay visible on the comment. An empty (0-record) base lock is
**empty-baseline growth**. Locally, `auctelis check` is the pre-push preflight.

```text
+ mcp "linear" → mcp.linear.app · network · tools · unpinned · publisher NOT VERIFIED
Needs approval from: @security
```

**Labels:** `GROWTH` | `REDUCTION` | `NONE`  
**Verdicts:** `LOCKED` | `BASELINE_NEEDED` | `NEEDS_REVIEW` | `BASELINE_ADOPTED` | `FAIL_CLOSED` | `PASS`

Agents must export `AUCTELIS_AGENT=1`; `lock`, `init`, and `ci init` are refused for agents
(`AUCTELIS_AGENT` is a speed bump, not a security control).

---

## Core commands

| Command | Purpose |
| --- | --- |
| `auctelis init --owner team` | Comment-only setup (`--enforce` for locked gate; `@` optional) |
| `auctelis` / `check` | Repo authority vs `AUTHORITY.lock` (front door) |
| `auctelis status [--check]` | Lock / workflow / CODEOWNERS / protection |
| `auctelis lock --update` | Write / refresh the committed lock |
| `auctelis gate --base-lock base.lock` | Tree-truth PR Authority Diff + CODEOWNERS gate |
| `auctelis diff --base <ref>` | Local PR Authority Diff simulator |
| `auctelis why <name>` | Exact config path / fields for one record |
| `auctelis demo` | Packaged fixture (optional) |

Host tripwires were removed in 0.8.0. The product gate is **tree-truth** —
research scan / annotate stay on `auctelis-dev` only and are not gate inputs.

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`REACH`](docs/REACH.md) · [`AUTHORITY-LOCK`](docs/AUTHORITY-LOCK.md) ·
[`AUCTELIS-GATE`](docs/AUCTELIS-GATE.md) · [index](docs/DOCUMENTATION-INDEX.md).

Pilots: [`docs/pilots/`](docs/pilots/).

---

## License

MIT — see [`LICENSE`](LICENSE).
