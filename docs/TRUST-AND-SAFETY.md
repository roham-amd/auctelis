# Trust and safety of the audit process

Permanent design requirements for authdiff. These are not optional precautions.

Related: [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md), [`POLICY.md`](POLICY.md),
[`SECURITY.md`](../SECURITY.md), [`skills/authdiff-auditor/SKILL.md`](../skills/authdiff-auditor/SKILL.md).

---

## Requirements

| Control | Requirement | How we meet it |
| --- | --- | --- |
| Input isolation | Target content is data, never trusted instructions | Skill + CLI treat target skills/READMEs as untrusted |
| Execution isolation | Passive mode does not execute target scripts, hooks, installers, launchers, or services | Default scan path is read-only; `run` / `snapshot --execute` are explicit opt-in |
| Filesystem safety | Bound traversal, file size, parser time, artifact count; handle symlinks | `CollectorLimits` + path containment in inventory I/O |
| Network safety | No outbound connections during passive inspection | Passive commands do not fetch remote MCP tools or install packages |
| Secret handling | Redact literal credentials in terminal/reports while preserving that a credential-like value was found | Findings cite evidence without echoing secrets; env values not hashed into digests |
| Policy integrity | PR authors cannot grant themselves trust | Action loads `.authdiff.yml` from base ref when `trusted-policy=true` |
| Provenance | Reports record assessed commit, scanner version, rules version, parsers | `findings.json` → `provenance` + evidence `rule_pack_version` / digests |
| Human approval | Lock and policy updates are reviewable | `AUTHORITY.lock` + CODEOWNERS + branch protection |
| Honest coverage | Unsupported surfaces never silently disappear | `coverage.adapter_matrix` + unparsed fail-closed |

## Authority layers (never conflate)

| Layer | Meaning |
| --- | --- |
| **Declared** | What the integration says it requires |
| **Configured** | What host/repo configuration appears to expose |
| **Effective** | What the execution environment actually permits |
| **Verified** | What an authorized test independently established |

A clean passive scan establishes **Declared/Configured** observations only.

## Biggest danger

An audit tool creating **false confidence** about something it did not inspect.

Prefer: *We could not establish this.*
