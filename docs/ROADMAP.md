# auctelis roadmap

**Product:** Authority Watch — package-lock for agent authority. See what your
agents can reach, and what changed since you last said OK.

**Current:** 0.4.0 · tooling 0.4.0 · rule pack 1.6 · policy contract 1.3

## Shipped in 0.4.0 (the 90-day shrink)

1. `auctelis watch` is the first screen: one card per authority change.
2. `watch --seal` replaces the separate `doctor → lock --home` ceremony.
3. Cursor hooks (`~/.cursor/hooks.json`) join Claude Code; Claude's PreToolUse
   matcher is `.*` so MCP calls reach the allowlist.
4. `hook status` reports wired / not firing for both hosts.
5. `scan`, `check`, `vet`, `explain`, `harden`, and SARIF are hidden from the
   default first screen (still callable).
6. One verdict dialect in the PR comment: `PASS` / `NEEDS_REVIEW` /
   `BASELINE_ADOPTED` / `FAIL_CLOSED`, with `GROWTH` / `REDUCTION` / `NONE` as
   labels.
7. `approved_findings[]` is emitted empty and never a gate input; CODEOWNERS is the approval system.
8. The first install block everywhere is the git tag, not PyPI.

## 30-day

| Window | Work |
| --- | --- |
| Days 1–3 | `watch` is the front door on a clean install. First run vs empty baseline is the aha; next line points at `--seal` / `--arm`. |
| Days 4–7 | Cursor + Claude hooks; Claude matcher `.*`; `hook status` says wired / not firing. |
| Week 2 | Hide the scanner surfaces; one verdict line; fix manifest, skill install line, playbook `--accept-gated`. |
| Week 3 | PyPI remains unpublished; keep the git tag as the documented path until the index returns 200. |
| Week 4 | Five eval fixtures are scored (`TP=4 FP=0 FN=0 TN=1`). Ask five outside people to run `watch` and say whether the line taught them something; write the answer (or leave empty) in `docs/pilots/TRACKER.md`. |

## 90-day decision gate

| Signal at week 4 / day 60 | Action |
| --- | --- |
| Five hosts still answer `hook status` as firing, or five repos still run the Action | Add optional URL-host pinning and a read-only MCP `check` tool. |
| Not five | Stop feature work. Publish the playbook as a Cursor rule; archive the scanner. |
| Fewer than five outside repos at day 60 | Kill criterion: fall back to [`PLAYBOOK.md`](PLAYBOOK.md) + slash commands. |

Do not add a 23rd rule, a badge, a web app, or an egress broker before a
stranger says the delta line taught them something.

## Kill list

- Public findings wall as the first screen; default SARIF upload.
- `explain` / `harden` / `vet` as top-level product jobs.
- `approvals[]` / `approved_findings[]` as gate inputs or written fields.
- Ecosystem-graph and audit-report schemas in the public story.
- A2A, typosquat, and broker modules until a pilot names them.
- Eval rows without a fixture.
- Any doc that says PyPI is the command to run today.

## Success metrics

- Minutes from install to the first delta line (target under 5).
- Hosts whose hook still answers `hook status` at week 4.
- Sessions with a non-empty delta that were resealed or reverted.
- PR comments a human replied to (not just green checks).
- Growth merges with protection `UNVERIFIED` (target 0).
- Published TP/FP on labeled configs before any detection claim.
- Pilot rows stay `_TBD_` until a repo exists.

Defer: MCP audit server, web Authority Cards, marketplace, runtime broker,
heavy AgentSecBench claims — until pilots demand them.

Detail: [`PRODUCT.md`](PRODUCT.md) · [`CHANGELOG.md`](../CHANGELOG.md) ·
[`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md) · [`pilots/`](pilots/).
