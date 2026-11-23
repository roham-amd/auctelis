# auctelis CLI reference

Primary command: **`auctelis`**.
Maintainer entry: **`auctelis-dev`** (build / lint / corpus / deps / validate / …).

Package `auctelis` **0.1.11** · product **0.1.11** · rule pack **1.6** (001–022).

Product contract / command tiers: [`PRODUCT.md`](PRODUCT.md) ·
reach: [`REACH.md`](REACH.md) ·
lock semantics: [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) ·
roadmap: [`ROADMAP.md`](ROADMAP.md).

Install: [`INSTALL.md`](INSTALL.md).

**Default:** bare `auctelis` runs `inspect`.

---

## Product command overview

| Tier | Command | Purpose |
| --- | --- | --- |
| Core | `inspect <target>` | 4-part Trust Dossier for a package, URL, or local path |
| Core | `inspect --local` | Read-only audit of installed local host configs |
| Core | `diff --base <ref>` | Local PR Authority Diff simulator |

Maintainer-only (`auctelis-dev`): legacy lockfile / gate / fleet commands
(`check`, `lock`, `gate`, `init`, `status`, `trust`, `why`, `demo`, `ci`),
plus `scan`, `annotate`, `build`, `lint`, `deps`, `corpus`, `hosts`,
`validate`, `inventory`, `verify`, `export`, `run`, `snapshot`,
`artifact-vet`. The host stack (`watch` / `allow` / `hook` / `doctor`) and
public `vet` / `harden` / `explain` CLIs were **removed**.

---

## `auctelis inspect`

```bash
auctelis inspect [TARGET] [--local] [--home PATH] [--json] [--markdown]
                 [--offline] [--out DIR]
```

Prints a 4-part Trust Dossier (`auctelis.trust_dossier.v1`) for a package,
launcher, URL, or local path. With `--local`, audits installed local host
configs across known agent paths (read-only; no hooks, no writes).

- `TARGET` — `npm:@scope/pkg`, `pypi:pkg`, `https://github.com/org/repo`,
  launcher form, or a local path (default: `.` when not `--local`)
- `--local` — host-config audit; cannot be combined with `TARGET`
- `--home PATH` — override home directory for `--local`
- `--json` — emit trust-dossier JSON
- `--markdown` — emit Trust Dossier Markdown
- `--offline` — local paths only (refuse remote/artifact fetches)
- `--out DIR` — write `dossier.json` and `dossier.md` under `DIR`

Zero-install published dossiers: [`dossiers/CATALOG.json`](../dossiers/CATALOG.json).
Request one via [IssueOps](../.github/ISSUE_TEMPLATE/inspect_request.yml).

---

## `auctelis diff --base`

```bash
auctelis diff --base <git-ref> [--repo PATH] [--json] [--markdown] [--out PATH]
auctelis diff lock <base.lock> <head.lock>
```

Local PR Authority Diff simulator: always extracts tree-truth authority from a
temporary detached worktree first (`baseline_state=tree`), matching the PR
Action. Falls back to a committed `AUTHORITY.lock` on the base ref
(`baseline_state=present`) only when worktree extract fails. When both succeed
and disagree, JSON sets `base_lock_drift=true` and text notes the drift.
Invalid ref → `FAIL_CLOSED`, exit 2. Regenerates head from the working tree and
prints the same comment dialect as the Action. Use `diff lock` to compare two
committed lock files directly.

- `--markdown` — emit PR-comment Markdown
- `--out PATH` — write Markdown output to `PATH`

---

## Maintainer (`auctelis-dev`)

```bash
auctelis-dev build all          # schemas, version parity, action parity, wheel lean
auctelis-dev build pypi-check   # Trusted Publishing cutover readiness (no publish)
auctelis-dev build schemas
auctelis-dev scan [PATH] [-o DIR] [--locked] [--base-lock PATH] [--fail-on never|high|any]
auctelis-dev annotate [findings.json] --format github|text|pr-comment
```

`build` / lint / corpus / deps stay maintainer-only. Annotation helpers are for
CI — not the product front door. Use `inspect` / `diff --base` for the public
path.

---

## Exit codes (summary)

| Command | `0` | `1` | `2` |
| --- | --- | --- |
| `inspect` | dossier printed | usage / target error | hard failure |
| `diff --base` | PASS (or BASELINE_NEEDED only if tree extract failed) | NEEDS_REVIEW | FAIL_CLOSED / invalid ref |

`BASELINE_ADOPTED` is emitted by the Action wrapper when a head lock arrives with
no trusted base lock; the `diff` CLI returns `PASS` / `NEEDS_REVIEW` /
`FAIL_CLOSED`.
