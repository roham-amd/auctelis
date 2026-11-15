# auctelis roadmap

**Product:** Project Trust — direnv allow for agent authority. Nothing in a repo
or your home gains reach until you've seen the diff and run allow/seal.

**Positioning:** the lockfile and one-line diff for what AI agents can reach.
Hooks are **tripwires**, not a sandbox. The scanner / gate / SARIF stack stays
callable but off the product path until pilots demand CI.

**Current:** 0.6.0 · lock schema 1 · tooling 0.6.0 · Project Trust north-star

## North star (direction #1 + #3)

1. Project Trust: home + project discovery, screen digest seal, per-project allow
2. Plugin-first distribution (Claude plugin + Cursor bundle; absolute hook paths)
3. Optional later: tool-description pinning (direction #2) after five outside users

## 30-day build (Project Trust)

| Window | Work |
| --- | --- |
| Week 1 | Permission-posture cards; curl\|sh host extract; show every sealed record; `seal --accept <digest>` |
| Week 2 | Project-level discovery (`.mcp.json`, `.claude/settings.json`, …) + `auctelis allow` store |
| Week 3 | Absolute-path hook install; per-host heartbeat; `hook status --probe`; fail-closed malformed stdin |
| Week 4 | Claude plugin + Cursor bundle under `plugins/`; recruit five outside users |

## 90-day decision gate

| Signal at day 60 | Action |
| --- | --- |
| Five hosts still answer `hook status` as firing (observed), or five outside repos | Optional destination pinning + read-only MCP `check_authority` |
| Not five | Stop feature work. Publish the playbook as a Cursor rule; keep scanner archived behind `auctelis-dev` / hidden commands |
| Fewer than five outside humans resealed or reverted once | Kill criterion: fold into [`PLAYBOOK.md`](PLAYBOOK.md) |

Do not add a 23rd rule, a badge, a web app, or an egress broker before a
stranger says the delta line taught them something.

## Kill list (product path)

- Scanner / SARIF / policy engine as the first screen
- `gate` / `ci init` / ruleset probe as required install ceremony
- Four-verdict vocabulary beyond what the watch actually needs for individuals
- Audit / ecosystem-graph schemas in the public story
- Calling PreToolUse “enforcement” (call it a **tripwire**)
- Mutable-tag Action as the documented front door once a SHA-pinned or App path exists
- Docker / PyPI ceremony until five outside users (git-tag install stays honest)

## Success metrics

- Minutes from install to first *project* delta (target under 3 after allow)
- Hosts whose per-host heartbeat still fires at day 30
- Share of non-empty deltas that end in allow or revert
- Outside pilots in [`pilots/TRACKER.md`](pilots/TRACKER.md) (leave `_TBD_` until real)

Detail: [`PRODUCT.md`](PRODUCT.md) · [`REACH.md`](REACH.md) · [`CHANGELOG.md`](../CHANGELOG.md)
