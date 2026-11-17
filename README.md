# Auctelis

**See what your AI agents can reach. Approve every change — in one PR comment.**

Auctelis inventories MCP servers, skills, hooks, instructions, and commands in a
repository, seals what you approved in `AUTHORITY.lock`, and posts one Authority
Diff when authority changes on a PR. It is a **consent ledger for agent reach**,
not a sandbox, certification, or marketplace badge.

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Reach: [`docs/REACH.md`](docs/REACH.md)

---

## First ten minutes

```bash
# Working install today (PyPI name reserved; package publish follows pilots):
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.12.0#subdirectory=tools"
auctelis --version

cd your-repo
auctelis check                    # aha: ranked reach cards (works with no lock)
auctelis check --pins             # unpinned npx/uvx MCP servers + exact fixes

# Local Authority Diff — works even if the base ref has no AUTHORITY.lock
# (verdict BASELINE_NEEDED; it does not write files).
auctelis diff --base origin/main

# Lockless (no init): paste templates/auctelis-diff.yml into .github/workflows/
# Or comment-only setup:
auctelis init --owner security    # advisory workflow + CODEOWNERS + lock
# PowerShell: omit @ — auctelis adds it. Use --enforce for locked gate.
# commit → PR → Authority Diff comment (only when authority changes)

auctelis trust mcp.linear.app     # optional: benign network reach stays advisory
auctelis status --check           # OK for comment-only; enforce says "verify in GitHub"
auctelis why linear               # exact config path for one name
```

On a PR, the Action diffs **tree-derived** base→head authority (committed lock
is drift-checked, never trusted as head) and posts the Authority Diff when
authority changed. Default `init` is **comment-only** (advisory); pass
`--enforce` for a required check. In comment-only mode, unreviewed growth is
`NEEDS_REVIEW` — never a false `PASS` — and no-change PRs stay quiet
(`comment-on-none: true` restores a comment on every PR). Auctelis **labels**
growth and posts the diff — it does **not** count PR approvals; GitHub
CODEOWNERS/rulesets do that when you enforce. Reach is tiered: inferred doc
links stay comment-only; execute/secrets/new MCP fail under `--enforce`.
Trusted destinations lower *network-only* reach to the comment tier but never
hide secrets, execute, approvals, or unattended reach. Body-only instruction
edits stay visible on the comment. An empty (0-record) base lock is
**empty-baseline growth**. Locally, `auctelis check` is the pre-push preflight.

```text
+ mcp "linear" launcher npx @ .cursor/mcp.json · execute · tools · unpinned · env: API_TOKEN · tier 2 (secrets) · publisher NOT VERIFIED · LITERAL_CONFIG
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
| `auctelis` / `check [--top N] [--pins]` | Ranked reach report vs `AUTHORITY.lock` (front door) |
| `auctelis diff --base <ref>` | Local Authority Diff; `BASELINE_NEEDED` when the ref has no lock |
| `auctelis trust <host>` | Trusted destinations for network-only reach (`--list`, `--remove`, `--init`) |
| `auctelis init --owner team` | Comment-only setup (`--enforce` for locked gate; `@` optional) |
| `auctelis status [--check]` | Lock / workflow / CODEOWNERS / protection (`--require-protection` for CI) |
| `auctelis lock --update` | Write / refresh the committed lock |
| `auctelis gate --base-lock base.lock` | Tree-truth PR Authority Diff + CODEOWNERS gate |
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
