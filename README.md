# Auctelis

**See what your AI agents can reach. Approve every change — in one PR comment.**

Auctelis inventories MCP servers, skills, hooks, instructions, and commands in a
repository, seals what you approved in `AUTHORITY.lock`, and posts one Authority
Diff when authority changes on a PR. It is a **consent ledger for agent reach**,
not a sandbox, certification, or marketplace badge.

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Reach: [`docs/REACH.md`](docs/REACH.md)

---

## First ten minutes

There are three surfaces: `check` locally, `rollout` to open Watch PRs, and the Action on later PRs.

```bash
# 1. See the aha — no install step, no lock needed (2 min):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools" auctelis check

# 2. Shareable audit artifact for your ticket / security lead (2 min):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools" auctelis check --report out/
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools" auctelis check --github your-org --report out/
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools" auctelis rollout out/reach-report.json
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools" auctelis rollout out/reach-report.json --apply

# 3. In one repo, pick one (2 min):
cd your-repo
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools" auctelis init --lockless          # one file: lockless PR Watch (no owner, no lock)
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools" auctelis init --owner security    # full setup: policy + workflow + CODEOWNERS + lock; add --enforce for a locked gate

# 4. Commit, open the install PR, and read the first-run "Watching …" comment (2 min).
#    Later no-change PRs stay silent; PRs that change agent authority get the Authority Diff.
```

The Action diffs **tree-derived** base→head authority (the committed lock is
drift-checked, never trusted as head) and posts the Authority Diff when authority
changed. Default `init` is **comment-only** (advisory); pass `--enforce` for a
required check. In comment-only mode, unreviewed **material (tier 1+)** growth is
`NEEDS_REVIEW` — never a false `PASS` — and no-change PRs stay quiet
(`comment-on-none: true` restores a comment on every PR). Tier-0 growth
(instructions-only edits and plain non-agent CI, including ordinary `secrets.*`)
stays `PASS` and quiet. Unpinned MCP growth includes a pasteable **Pin fix**
line. The PR that adds the Auctelis workflow posts one "Watching" comment as
proof the gate is live, then silence is the product.

Auctelis **labels** growth and posts the diff — it does **not** count PR
approvals; GitHub CODEOWNERS/rulesets do that when you enforce. Reach is tiered:
inferred doc links stay comment-only; literal execute/secrets/new MCP fail under
`--enforce`. Trusted destinations lower *network-only* reach to the comment tier
but never hide secrets, execute, approvals, unattended reach, a record that
declares a launcher, or new **MCP / Hook / Host Settings** authority. Body-only
instruction edits stay visible on the comment. An empty (0-record) base lock is
**empty-baseline growth**. Locally, `auctelis check` is the pre-push preflight.

```text
+ mcp "linear" launcher npx @ .cursor/mcp.json · execute · tools · unpinned · env: API_TOKEN · tier 2 (secrets) · LITERAL_CONFIG
Needs approval from: @security
```

**Labels:** `GROWTH` | `REDUCTION` | `NONE`  
**Verdicts:** `LOCKED` | `BASELINE_NEEDED` | `NEEDS_REVIEW` | `BASELINE_ADOPTED` | `FAIL_CLOSED` | `PASS`

Agents must export `AUCTELIS_AGENT=1`; `lock`, `init`, and `ci init` are refused for agents
(`AUCTELIS_AGENT` is a speed bump, not a security control).

---

## Advanced (not part of the first ten minutes)

Everything below is a power-user surface. None of it is required for the two
surfaces above.

| Command | Purpose |
| --- | --- |
| `auctelis diff --base <ref>` | Local Authority Diff; lockless refs use tree-truth (`baseline_state=tree`) |
| `auctelis check --report DIR` | Shareable HTML+MD+JSON+SBOM reach report |
| `auctelis check --pins` | Unpinned npx/uvx MCP servers + exact pin fixes |
| `auctelis trust <host>` | Trusted destinations for network-only reach (`--list`, `--remove`, `--init`) |
| `auctelis status [--check]` | Lock / workflow / CODEOWNERS / protection status |
| `auctelis lock --update` | Write / refresh the committed lock |
| `auctelis gate --base-lock base.lock` | Tree-truth PR Authority Diff + CODEOWNERS gate |
| `auctelis why <name>` | Exact config path / fields for one record |
| `auctelis demo` | Packaged fixture (optional) |

Lockless alternative to full `init`: `auctelis init --lockless` writes
[`tools/auctelis/templates/auctelis-diff.yml`](tools/auctelis/templates/auctelis-diff.yml)
to `.github/workflows/auctelis.yml` (no owner, lock, policy, or CODEOWNERS).
Auditing several repos at once: `auctelis check repo-a repo-b --report out/`
writes one ranked fleet report.

Persistent CLI install (git tag; see docs/INSTALL.md):

```bash
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.1.4#subdirectory=tools"
```

Host tripwires were removed. The product gate is **tree-truth** —
research scan / annotate stay on `auctelis-dev` only and are not gate inputs.

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`REACH`](docs/REACH.md) · [`AUTHORITY-LOCK`](docs/AUTHORITY-LOCK.md) ·
[`AUCTELIS-GATE`](docs/AUCTELIS-GATE.md) · [index](docs/DOCUMENTATION-INDEX.md).

Pilots: [`docs/pilots/`](docs/pilots/).

---

## License

MIT — see [`LICENSE`](LICENSE).
