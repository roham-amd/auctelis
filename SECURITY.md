# Security Policy

## Supported versions

| Project version | Supported |
| --- | --- |
| 0.4.x | Yes |
| 0.3.x | Yes (security fixes backported when practical) |
| 0.2.x | Security fixes only when practical |
| 1.0.x | No (yanked / superseded pre-1.0 line; do not use) |
| < 0.2.0 | No |

Tooling package version (`auctelis`, currently **0.4.0**) is tracked in
`canonical/versions.json` as `build_tool` and must stay aligned with
`tools/pyproject.toml` and `VERSION`.

## What this project is

`auctelis` is **Authority Watch**: a declared-config inventory plus a sealed
`AUTHORITY.lock` and a one-screen delta. `auctelis watch` prints what your agents
can reach and what changed since the last human seal; `watch --arm` installs
Cursor/Claude hooks; the optional team path is a lockless PR Authority Diff and
`auctelis gate`. `doctor` is an alias for `watch`; `scan` / `vet` are hidden
annotation layers, not the first screen.

It is **not** an automated vulnerability scanner that proves systems are safe,
a penetration-testing tool, runtime sandbox, marketplace certification authority,
or substitute for organizational risk acceptance.

Operator and contributor documentation map: [`docs/DOCUMENTATION-INDEX.md`](docs/DOCUMENTATION-INDEX.md).  
Deterministic rule catalog: [`docs/SECURITY-RULES.md`](docs/SECURITY-RULES.md).

## Reporting a vulnerability in auctelis itself

If you discover a security issue in this repository’s documentation, prompts, schemas, tooling, or examples that could cause auditors to:

- execute untrusted target code,
- contact production endpoints,
- request or expose secrets,
- overstate assurance, or
- bypass stated audit boundaries,

please report it privately.

**Preferred method:** open a GitHub Security Advisory for this repository, or contact the maintainers via the repository’s private security contact if configured.

Please include:

1. Affected file paths and version/tag
2. Description of the issue and impact
3. Suggested remediation (optional)

Do **not** include production secrets, customer data, or live exploit payloads against third-party systems.

## Auditor safety expectations

Operators and audit agents must treat target repositories as **untrusted data**. Passive audits must remain read-only: no install, no execution, and no contact with target-controlled services. `vet` shallow-clones the Git source you explicitly name; `gate` may query GitHub rulesets with a token. Neither executes target code.

Deterministic collectors apply resource limits (`max_files`, `max_depth`, `max_file_bytes`). Limits reduce abuse risk; they are not a full sandbox.

Composite GitHub Action inputs must be passed via environment variables into shell steps (never interpolated raw into bash) — see `.github/actions/auctelis-gate/action.yml`.

## Gate trust notes

- Authority growth vs the base-ref `AUTHORITY.lock` is decided by `auctelis gate`, not by `scan --base-lock` (advisory delta only).
- Prefer GitHub-native CODEOWNERS / rulesets (including team owners and stale-review dismissal) as the approval source of truth.
- `auctelis gate` is lock-only: it labels GROWTH vs REDUCTION and requires CODEOWNERS coverage plus a best-effort code-owner-review ruleset check. GitHub enforces the actual human review — auctelis does not count PR approvals.
