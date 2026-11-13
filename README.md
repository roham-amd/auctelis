# Auctelis

**Package-lock for agent authority**

> See what your agents can do, and what changed since you last said OK.

Auctelis maps MCP servers, skills, and host agent config on your laptop, seals
an approved state in `AUTHORITY.lock`, and shouts when authority grows — in a
session hook or a PR comment. Enforcement stays with GitHub (CODEOWNERS /
rulesets). Deterministic tooling is the source of truth; an agent is an optional
explainer.

It is **not** a certification, marketplace badge, runtime sandbox, or substitute
for organizational risk acceptance. Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md).

---

## First five minutes (Authority Watch)

```bash
# Install from the pinned kit tag (PyPI path once published: uvx auctelis doctor)
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.3.4#subdirectory=tools" auctelis doctor

uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.3.4#subdirectory=tools"

auctelis doctor              # host map: secrets, network, unpinned
auctelis lock --home         # seal ~/.auctelis/AUTHORITY.lock
auctelis hook install        # session-start delta + PreToolUse lock enforce
auctelis doctor --since-lock # one-screen delta (hooks call this)
auctelis vet github.com/org/some-skill
```

After the next MCP add, a new agent session prints only the delta
(`+1 MCP x: network, secrets, unpinned`). Unchanged hosts stay quiet.

**Verdict language (one):** `PASS` | `GROWTH` | `NEEDS_REVIEW` | `BASELINE_ADOPTED`.
Scan severities annotate the diff; they are not a second public `BLOCK` gate.

Agents must export `AUCTELIS_AGENT=1` so lock / policy mutations are refused.

---

## Team upsell (PR Authority Diff)

Lockless-first — one Action line, no baseline ceremony:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- run: >
    pip install
    "git+https://github.com/roham-amd/auctelis.git@v0.3.4#subdirectory=tools"
# Prefer: uses: …/auctelis-gate@<commit-sha>
- uses: roham-amd/auctelis/.github/actions/auctelis-gate@v0.3.4
  with:
    path: .
    trusted-policy: "true"
    authority-diff: "true"
    locked: "false"          # quickstart: post the diff, no lock required
    strict-ruleset: "true"   # UNVERIFIED protection fails growth
    install-tools-from: path
```

Approved-state upgrade: commit `AUTHORITY.lock`, set `locked: true`, then
`auctelis ci init --owner @team` for CODEOWNERS + workflow.

Full example: [`docs/auctelis-consumer-gate.example.yml`](docs/auctelis-consumer-gate.example.yml).
Gate docs: [`docs/AUCTELIS-GATE.md`](docs/AUCTELIS-GATE.md).

---

## Core commands

| Command | Purpose |
| --- | --- |
| `auctelis doctor` | Host authority map (front door) |
| `auctelis lock --home` / `lock` | Seal host or repo `AUTHORITY.lock` |
| `auctelis hook install` | Session-start delta + PreToolUse lock hook |
| `auctelis vet` | Pre-install annotations |
| `auctelis gate` | Label growth vs `--base-lock` (strict ruleset default) |
| `auctelis ci init --owner @user` | Policy + workflow + CODEOWNERS |
| `auctelis demo` | Packaged evil fixture (optional) |

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`AUCTELIS-GATE`](docs/AUCTELIS-GATE.md) · [`PLAYBOOK`](docs/PLAYBOOK.md) ·
[index](docs/DOCUMENTATION-INDEX.md).

Pilots / kill criterion: [`docs/pilots/`](docs/pilots/). Eval labels: [`eval/`](eval/).

---

## License

MIT — see [`LICENSE`](LICENSE).
