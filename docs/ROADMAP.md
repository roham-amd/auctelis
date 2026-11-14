# auctelis roadmap

**Product:** Authority Watch — package-lock for agent authority. See what your
agents can reach, and what changed since you last said OK.

**Positioning:** the lockfile and one-line diff for what AI agents can reach.
Hooks are **tripwires**, not a sandbox. The scanner / gate / SARIF stack stays
callable but off the product path until pilots demand CI.

**Current:** 0.5.0 · lock schema 1 · tooling 0.5.0

## North star (direction #1 + #2)

1. Lockfile standard + dead-simple delta CLI (`watch` / `--seal` / `--arm` / `why`)
2. Observed consent hooks for Claude Code + Cursor (heartbeat + ledger)

## 30-day build (in progress)

| Window | Work |
| --- | --- |
| Week 1 | Schema v1 + reach spec; first-run highlights only; demote gate/scanner from help; tripwire language |
| Week 2 | PyPI trusted publishing (workflow ready); install docs stay git-tag until PyPI 200; OS matrix for pytest |
| Week 3 | First-run UX + `auctelis why`; watch JSON `schema_version`; exit codes frozen (0 quiet / 1 delta / 2 lock error) |
| Week 4 | Hook heartbeat + ledger; `hook status` = wired / not yet observed / firing; truthfulness tests |

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

## Success metrics

- Minutes from install to first *change* delta (target under 3 after seal)
- Hosts whose heartbeat still fires at day 30
- Sessions with a non-empty delta that were resealed or reverted
- Outside pilots in [`pilots/TRACKER.md`](pilots/TRACKER.md) (leave `_TBD_` until real)

Detail: [`PRODUCT.md`](PRODUCT.md) · [`REACH.md`](REACH.md) · [`CHANGELOG.md`](../CHANGELOG.md)
