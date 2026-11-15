# Auctelis

**Package-lock for agent authority**

> See what your agents can reach, and what changed since you last said OK.

Auctelis inventories the MCP servers, skills, hooks, and commands your agents
can use, seals what you approved in `AUTHORITY.lock`, and prints one line when
that reach changes — at session start. It is a **consent ledger**, not a
certification, runtime sandbox, or marketplace badge.

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Reach: [`docs/REACH.md`](docs/REACH.md)

---

## First three minutes

```bash
# Git tag is the supported install until the PyPI package returns 200.
uv tool install --python 3.12 \
  "git+https://github.com/roham-amd/auctelis.git@v0.6.0#subdirectory=tools"

auctelis                        # every sealable record + Accept digest
auctelis watch --seal --accept <digest>   # human baseline (digest from the screen)
auctelis allow                  # allow this project's authority hash
auctelis watch --arm            # session + tripwire hooks (absolute paths)
auctelis hook status --probe    # prove each wired tripwire denies
auctelis why linear             # exact config path for one name
```

First run shows **every record that will be sealed** (including host permission
posture) and an Accept digest. After you seal, a new MCP server or permission
escalation prints one line. Unchanged hosts stay quiet.

```text
+ mcp "linear" → mcp.linear.app · network · tools · unpinned · publisher NOT VERIFIED
```

**Labels:** `GROWTH` | `REDUCTION` | `NONE` (what the lock delta is).

Hooks are **tripwires**, not a sandbox — an agent can still route around them.
Agents must export `AUCTELIS_AGENT=1`; `watch --seal`, `watch --arm`,
`hook install`, and `lock` are refused for agents.

---

## Core commands

| Command | Purpose |
| --- | --- |
| `auctelis` / `watch` | One-screen declared authority (front door) |
| `auctelis watch --seal --accept <digest>` | Seal the human baseline (digest from screen) |
| `auctelis allow` | Allow current project authority hash |
| `auctelis watch --arm` | Install session + tripwire hooks |
| `auctelis why <name>` | Exact config path / fields for one record |
| `auctelis hook status [--probe]` | Wired / firing per host; optional tripwire probe |
| `auctelis demo` | Packaged fixture (optional) |

`scan` / `gate` / `ci` / `vet` / `explain` / `harden` remain callable for
existing scripts but are hidden from default help. The scanner is an annotation
layer, not the product.

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`REACH`](docs/REACH.md) · [`AUTHORITY-LOCK`](docs/AUTHORITY-LOCK.md) ·
[index](docs/DOCUMENTATION-INDEX.md).

Pilots: [`docs/pilots/`](docs/pilots/).

---

## License

MIT — see [`LICENSE`](LICENSE).
