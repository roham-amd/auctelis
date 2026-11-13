# auctelis — decision report

Decision-oriented scan summary. Capability observations are not vulnerabilities.
Absence of findings is not evidence of safety when coverage is incomplete.

```text
auctelis — Authority Diff for AI agents
Product: auctelis 0.3.1  (tooling 0.3.1)
Repository: C:\Users\rohaa\Projects\auctelis\examples\demo-vulnerable
Commit: 827a4f339dee9add20a1f4b11bc63d5ba975b562

DECISION: BLOCK
  BLOCK: 7 high/critical authority issue(s) require a fix or explicit risk acceptance before merge/install.
  Observed 11 gated finding(s) and 2 capability observation(s).
  Next: `auctelis explain F-00N` for evidence, or `auctelis fix` for dry-run fix patches.
  Coverage: 20% SUPPORTED (1/5); PARTIAL=4 MANUAL_ONLY=0 — clean result ≠ safe.

DECISION SUMMARY
  Components discovered              5
  Authority-bearing components       4
  External connections               2
  High-priority review items         7
  Unverified control surfaces        4

OBSERVATION CLASSES
  Security findings                  8
  Exposure observations              3
  Capability observations            2

AUTHORITY SURFACES (review required)
  [CRITICAL] F-004  Download-and-execute pattern in agent surface
      class: SECURITY_FINDING  confidence: OBSERVED
      evidence: skills/bootstrap/SKILL.md:17
      action: Vendor and pin scripts; never curl|sh from skills or hooks.
  [CRITICAL] F-008  Literal secret-like value in MCP env
      class: SECURITY_FINDING  confidence: OBSERVED
      evidence: .cursor/mcp.json:6
      action: Replace literal values with `${ENV}` references; rotate the secret.
  [CRITICAL] F-009  Unpinned MCP launcher with secret-bearing env
      class: SECURITY_FINDING  confidence: OBSERVED
      evidence: .cursor/mcp.json:4
      action: Pin the package and replace env literals with ${ENV} references.
  [HIGH] F-005  Permission-bypass or auto-approve flag in agent surface
      class: SECURITY_FINDING  confidence: OBSERVED
      evidence: skills/bootstrap/SKILL.md:11
      action: Remove bypass flags; keep approval required for privileged actions.
  [HIGH] F-007  MCP server launched via unpinned package installer
      class: SECURITY_FINDING  confidence: OBSERVED
      evidence: .cursor/mcp.json:4
      action: Pin an exact version or digest; avoid `npx -y` / floating `uvx` tags.

EXAMPLE AUTHORITY PATH
  skills/bootstrap/SKILL.md
  → Reviewed instructions → unreviewed remote script
  → Arbitrary remote code execution
  [SECURITY_FINDING] F-004: Download-and-execute pattern in agent surface
  Next: Vendor and pin scripts; never curl|sh from skills or hooks.

COMPONENTS BY TYPE
  Agent Host               1
  CI Workflow              1
  MCP Server Registration  2
  Skill                    1

ALL FINDINGS
  CRITICAL 3  HIGH 4  MEDIUM 3  LOW 1  INFO 2
  [SECURITY_FINDING/CRITICAL/OBSERVED] F-004 Download-and-execute pattern in agent surface
      evidence: skills/bootstrap/SKILL.md:17
      action: Vendor and pin scripts; never curl|sh from skills or hooks.
  [SECURITY_FINDING/CRITICAL/OBSERVED] F-008 Literal secret-like value in MCP env
      evidence: .cursor/mcp.json:6
      action: Replace literal values with `${ENV}` references; rotate the secret.
  [SECURITY_FINDING/CRITICAL/OBSERVED] F-009 Unpinned MCP launcher with secret-bearing env
      evidence: .cursor/mcp.json:4
      action: Pin the package and replace env literals with ${ENV} references.
  [SECURITY_FINDING/HIGH/OBSERVED] F-005 Permission-bypass or auto-approve flag in agent surface
      evidence: skills/bootstrap/SKILL.md:11
      action: Remove bypass flags; keep approval required for privileged actions.
  [SECURITY_FINDING/HIGH/OBSERVED] F-007 MCP server launched via unpinned package installer
      evidence: .cursor/mcp.json:4
      action: Pin an exact version or digest; avoid `npx -y` / floating `uvx` tags.
  [SECURITY_FINDING/HIGH/OBSERVED] F-011 Remote MCP endpoint uses cleartext HTTP
      evidence: .cursor/mcp.json:11
      action: Use https:// only; reject plain HTTP remote MCP registrations.
  [SECURITY_FINDING/HIGH/OBSERVED] F-013 pull_request_target workflow invokes agent-related steps
      evidence: .github/workflows/agent.yml:3
      action: Prefer pull_request; never feed fork PR code to privileged agents.
  [SECURITY_FINDING/MEDIUM/OBSERVED] F-012 Unattended automation or CI workflow present
      evidence: .github/workflows/agent.yml
      action: Confirm agent/MCP steps need this workflow; pin launchers; least-privilege tokens.
  [EXPOSURE/MEDIUM/OBSERVED] F-003 Instruction text directs hide, bypass, or fetch-execute behavior
      evidence: skills/bootstrap/SKILL.md
      action: Rewrite instructions; forbid hide/bypass/remote-exec directives in skills.
  [EXPOSURE/MEDIUM/OBSERVED] F-010 MCP server uses remote endpoint
      evidence: .cursor/mcp.json:11
      action: Verify endpoint identity, TLS, OAuth scopes, and whether secrets are forwarded.
  [EXPOSURE/LOW/OBSERVED] F-002 Skill references external URLs
      evidence: skills/bootstrap/SKILL.md:17
      action: Pin or vendor remote references; treat remote content as untrusted.
  [CAPABILITY/INFORMATIONAL/POTENTIAL] F-001 Skill references executable scripts
      evidence: skills/bootstrap/SKILL.md:10
      action: Treat as an authority surface: verify whether scripts inherit sensitive environment variables and whether execution requires independent approval.

COVERAGE
  Deterministically discovered  5
  Adapter maturity              {'SUPPORTED': 1, 'PARTIAL': 4, 'MANUAL_ONLY': 0, 'UNSUPPORTED': 0}

ADAPTER COVERAGE
  Skill                        SUPPORTED    skill_md
  MCP                          PARTIAL      mcp_config
  MCP server source            PARTIAL      mcp_server_source
  A2A                          PARTIAL      a2a_agent_card
  Instruction rules            SUPPORTED    instruction_rules
  Hook                         PARTIAL      hooks
  Plugin                       PARTIAL      plugins
  Subagent                     PARTIAL      subagents
  Automation                   PARTIAL      automations
  CI / GitHub Actions          PARTIAL      github_workflows
  Host effective permissions   PARTIAL      host_profiles
  Browser agents               MANUAL_ONLY  —
  Memory / RAG                 MANUAL_ONLY  —
  Model providers              MANUAL_ONLY  —
  Multimodal artifacts         MANUAL_ONLY  —
  Runtime behavior             UNSUPPORTED  —
  Publisher / artifact provenance MANUAL_ONLY  —

NOT VERIFIED
  - Runtime behavior
  - Publisher identity
  - Effective host permissions
  - Credential isolation
  Manual-only / unsupported families:
    - Browser agents
    - Memory / RAG
    - Model providers
    - Multimodal artifacts
    - Runtime behavior
    - Publisher / artifact provenance

RESIDUAL RISK / NEXT ACTIONS
  1. Review AUTHORITY SURFACES above before install/merge/deploy.
  2. `auctelis lock` then protect AUTHORITY.lock with CODEOWNERS.
  3. `auctelis explain F-00N` for evidence, attack path, and remediation.
  4. Optional AI deep review: skills/auctelis-auditor (consumes this evidence).

IMPORTANT
  Capability ≠ vulnerability. Exposure ≠ confirmed exploit.
  Incomplete coverage never equals safety.
  Observed / Potential / Not verified remain distinct from Verified impact.
```

## Critical / high findings

- **F-004** [SECURITY_FINDING/CRITICAL/OBSERVED] Download-and-execute pattern in agent surface
  - Evidence: `skills/bootstrap/SKILL.md:17`
  - Action: Vendor and pin scripts; never curl|sh from skills or hooks.
- **F-008** [SECURITY_FINDING/CRITICAL/OBSERVED] Literal secret-like value in MCP env
  - Evidence: `.cursor/mcp.json:6`
  - Action: Replace literal values with `${ENV}` references; rotate the secret.
- **F-009** [SECURITY_FINDING/CRITICAL/OBSERVED] Unpinned MCP launcher with secret-bearing env
  - Evidence: `.cursor/mcp.json:4`
  - Action: Pin the package and replace env literals with ${ENV} references.
- **F-005** [SECURITY_FINDING/HIGH/OBSERVED] Permission-bypass or auto-approve flag in agent surface
  - Evidence: `skills/bootstrap/SKILL.md:11`
  - Action: Remove bypass flags; keep approval required for privileged actions.
- **F-007** [SECURITY_FINDING/HIGH/OBSERVED] MCP server launched via unpinned package installer
  - Evidence: `.cursor/mcp.json:4`
  - Action: Pin an exact version or digest; avoid `npx -y` / floating `uvx` tags.
- **F-011** [SECURITY_FINDING/HIGH/OBSERVED] Remote MCP endpoint uses cleartext HTTP
  - Evidence: `.cursor/mcp.json:11`
  - Action: Use https:// only; reject plain HTTP remote MCP registrations.
- **F-013** [SECURITY_FINDING/HIGH/OBSERVED] pull_request_target workflow invokes agent-related steps
  - Evidence: `.github/workflows/agent.yml:3`
  - Action: Prefer pull_request; never feed fork PR code to privileged agents.

## All findings

- **F-004** [SECURITY_FINDING/CRITICAL/OBSERVED] Download-and-execute pattern in agent surface
  - Vendor and pin scripts; never curl|sh from skills or hooks.
- **F-008** [SECURITY_FINDING/CRITICAL/OBSERVED] Literal secret-like value in MCP env
  - Replace literal values with `${ENV}` references; rotate the secret.
- **F-009** [SECURITY_FINDING/CRITICAL/OBSERVED] Unpinned MCP launcher with secret-bearing env
  - Pin the package and replace env literals with ${ENV} references.
- **F-005** [SECURITY_FINDING/HIGH/OBSERVED] Permission-bypass or auto-approve flag in agent surface
  - Remove bypass flags; keep approval required for privileged actions.
- **F-007** [SECURITY_FINDING/HIGH/OBSERVED] MCP server launched via unpinned package installer
  - Pin an exact version or digest; avoid `npx -y` / floating `uvx` tags.
- **F-011** [SECURITY_FINDING/HIGH/OBSERVED] Remote MCP endpoint uses cleartext HTTP
  - Use https:// only; reject plain HTTP remote MCP registrations.
- **F-013** [SECURITY_FINDING/HIGH/OBSERVED] pull_request_target workflow invokes agent-related steps
  - Prefer pull_request; never feed fork PR code to privileged agents.
- **F-012** [SECURITY_FINDING/MEDIUM/OBSERVED] Unattended automation or CI workflow present
  - Confirm agent/MCP steps need this workflow; pin launchers; least-privilege tokens.
- **F-003** [EXPOSURE/MEDIUM/OBSERVED] Instruction text directs hide, bypass, or fetch-execute behavior
  - Rewrite instructions; forbid hide/bypass/remote-exec directives in skills.
- **F-010** [EXPOSURE/MEDIUM/OBSERVED] MCP server uses remote endpoint
  - Verify endpoint identity, TLS, OAuth scopes, and whether secrets are forwarded.
- **F-002** [EXPOSURE/LOW/OBSERVED] Skill references external URLs
  - Pin or vendor remote references; treat remote content as untrusted.
- **F-001** [CAPABILITY/INFORMATIONAL/POTENTIAL] Skill references executable scripts
  - Treat as an authority surface: verify whether scripts inherit sensitive environment variables and whether execution requires independent approval.
- **F-006** [CAPABILITY/INFORMATIONAL/OBSERVED] MCP local command sets non-secret environment
  - Record as an execution capability; verify host isolation before treating as risk.

## Unverified areas

- Runtime behavior
- Publisher identity
- Effective host permissions
- Credential isolation
- Manual-only family: Browser agents
- Manual-only family: Memory / RAG
- Manual-only family: Model providers
- Manual-only family: Multimodal artifacts
- Manual-only family: Runtime behavior
- Manual-only family: Publisher / artifact provenance

## Residual risk questions (human judgment required)

1. What authority does this ecosystem introduce, and who receives it?
2. What newly changed since the baseline?
3. What must be fixed before install / merge / deploy?
4. What remains unverified and must be explicitly accepted?
