# auctelis roadmap

**Product:** Authority Watch — package-lock for agent authority. See what your
agents can do, and what changed since you last said OK.

**Current:** 0.3.4 · tooling 0.3.4 · rule pack 1.6 · policy contract 1.3

## Shipped in 0.3.4 (Days 1–3 + Weeks 2–4 scaffolding)

1. Wheel starts without `packaging` (lazy maintainer imports).
2. `release.yml` requires `pip-audit` + `wheel-smoke` + `auctelis --version`.
3. `auctelis hook install` (session-start delta + PreToolUse lock enforce).
4. Lockless-first Action (`locked` default false); `strict-ruleset` default true.
5. One verdict vocabulary; PR comment cleanup; eval/configs scaffold.

## 30-day

| Window | Work |
| --- | --- |
| Days 1–3 | Install honesty: green `main`, cut `v0.3.4`, publish PyPI when Trusted Publishing is live |
| Weeks 2–3 | Hook retention; lockless quickstart dogfood; PR comment polish in pilots |
| Week 4 | Recruit five pilots; label ≥25 configs in `eval/` |

## 90-day

| Work | Status |
| --- | --- |
| Lock-enforcing PreToolUse (deny MCP not in lock) | Shipped in hook template |
| First published FP/FN numbers | Scaffold ready — needs labeled rows |
| `--strict-ruleset` Action default | Shipped |
| Read-only MCP server | Decide from pilot demand (still deferred) |
| Day-60 kill criterion | Unchanged |

**Kill if** fewer than five outside repos keep the check enabled by day 60 →
fall back to [`PLAYBOOK.md`](PLAYBOOK.md) + slash commands.

## Kill list

- Scanner public `BLOCK` / SARIF as a gate language (annotations + optional export only).
- `approvals[]` / `approved_findings[]` as gate inputs (decorative / empty).
- Product front-door for `auctelis-dev run` / `snapshot` / `artifact-vet`.
- GitHub Packages as a required distribute path (optional / best-effort).
- Ecosystem-graph and audit-report schemas from the public contract narrative.
- Docs surface trimmed to ~5 public pages (see [`DOCUMENTATION-INDEX.md`](DOCUMENTATION-INDEX.md)).

## Success metrics

- Outside repos still running the check at day 30 (target 5 by day 60).
- Minutes from install to first lock (target under 5).
- Hosts with the hook still installed at week 4.
- Published TP/FP rate on labeled configs.
- Reviewer-confirmed "I wouldn't have noticed this" events per pilot.
- Share of growth PRs merged with protection `UNVERIFIED` (target 0).

Defer: MCP audit server, web Authority Cards, marketplace, runtime broker,
heavy AgentSecBench claims — until pilots demand them.

Detail: [`PRODUCT.md`](PRODUCT.md) · [`CHANGELOG.md`](../CHANGELOG.md) ·
[`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md) · [`pilots/`](pilots/).
