# Security Policy

## Supported versions

| Project version | Supported |
| --- | --- |
| 1.0.x | Yes |
| < 1.0.0 | No |

Tooling package version (`authdiff`, currently **1.0.0**) is tracked in
`canonical/versions.json` as `build_tool` and must stay aligned with
`tools/pyproject.toml` and `tools/authdiff/__init__.py`.

## What this project is

`authdiff` is a **lockfile + Authority Diff** for AI-agent ecosystems: host doctor,
pre-install vet, deterministic repo scan (`authdiff scan` / `lock` / `check --locked`),
CI gate with trusted policy, and an optional AI auditor skill.

It is **not** an automated vulnerability scanner that proves systems are safe,
a penetration-testing tool, runtime sandbox, marketplace certification authority,
or substitute for organizational risk acceptance.

Operator and contributor documentation map: [`docs/DOCUMENTATION-INDEX.md`](docs/DOCUMENTATION-INDEX.md).  
Threats against the toolchain itself: [`docs/archive/toolchain-threat-model.md`](docs/archive/toolchain-threat-model.md).  
Deterministic rule catalog: [`docs/SECURITY-RULES.md`](docs/SECURITY-RULES.md).

## Reporting a vulnerability in authdiff itself

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

Operators and audit agents must treat target repositories as **untrusted data**. Passive audits must remain read-only: no install, no execute, no contact with target-controlled services. See `archive/methodology/prompts/04-passive-guardrails.md` and [`docs/archive/toolchain-threat-model.md`](docs/archive/toolchain-threat-model.md).

Deterministic collectors apply resource limits (`max_files`, `max_depth`, `max_file_bytes`). Limits reduce abuse risk; they are not a full sandbox.

Composite GitHub Action inputs must be passed via environment variables into shell steps (never interpolated raw into bash) — see `.github/actions/authdiff-gate/action.yml`.
