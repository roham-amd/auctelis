"""Versioned deterministic security rules for authdiff.

Rules classify outputs as CAPABILITY, EXPOSURE, or SECURITY_FINDING.
Presence of a security-relevant capability is not automatically a HIGH finding.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from authdiff.security.evidence_util import EvidenceContext, build_rule_evidence
from authdiff.security.models import (
    Evidence,
    EvidenceStrength,
    Finding,
    FindingClass,
    Severity,
    VerificationStatus,
)

RuleFn = Callable[[dict[str, Any], list[Evidence], list[Finding], EvidenceContext], None]


def _label(component: dict[str, Any]) -> str:
    """Sanitize attacker-controlled names before embedding in finding prose."""
    from authdiff.export.pr_comment import escape_markdown

    raw = str(component.get("name") or component.get("component_id") or "unnamed")
    return escape_markdown(raw, max_len=80).replace("`", "'")


@dataclass(frozen=True, slots=True)
class RuleSpec:
    rule_id: str
    title: str
    version: str
    apply: RuleFn


def _add_finding(
    findings: list[Finding],
    *,
    rule_id: str,
    title: str,
    severity: Severity,
    confidence: VerificationStatus,
    description: str,
    component: dict[str, Any],
    evidence: Evidence,
    capabilities: list[str],
    attacker_control: str,
    entry_point: str,
    trust_boundary: str,
    impact: str,
    missing_controls: list[str],
    recommended_action: str,
    finding_class: FindingClass,
    exposure: str = "REPO_CONFIG",
    evidence_strength: EvidenceStrength = "INFERRED_HINT",
    verify_in_60s: str = "",
    fix_snippet: str = "",
) -> None:
    fid = f"F-{len(findings) + 1:03d}"
    findings.append(
        Finding(
            finding_id=fid,
            rule_id=rule_id,
            title=title,
            severity=severity,
            confidence=confidence,
            description=description,
            component_ids=[str(component.get("component_id") or "")],
            evidence_ids=[evidence.evidence_id],
            capabilities=capabilities,
            attacker_control=attacker_control,
            entry_point=entry_point,
            trust_boundary=trust_boundary,
            impact=impact,
            missing_controls=missing_controls,
            recommended_action=recommended_action,
            exploitability="UNKNOWN",
            exposure=exposure,
            finding_class=finding_class,
            evidence_strength=evidence_strength,
            verify_in_60s=verify_in_60s,
            fix_snippet=fix_snippet,
        )
    )


def rule_skill_bundled_scripts(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "Skill":
        return
    hints = set(component.get("priority_hints") or [])
    if not hints.intersection(
        {"bundled_scripts_directory", "script_reference", "possible_code_execution_reference"}
    ):
        return
    # Capability observation unless stronger host/credential evidence exists.
    # HIGH requires literal bundled scripts *and* credential handling with
    # executable evidence — bag-of-words alone must not escalate.
    finding_class: FindingClass = "CAPABILITY"
    severity: Severity = "INFORMATIONAL"
    strength: EvidenceStrength = "INFERRED_HINT"
    if (
        "bundled_scripts_directory" in hints
        and "secrets_or_credential_handling" in hints
        and "executable_evidence" in hints
    ):
        finding_class = "SECURITY_FINDING"
        severity = "HIGH"
        strength = "INFERRED_HINT"  # still inferred: scripts + wording, not a proven exfil path
    elif "bundled_scripts_directory" in hints:
        finding_class = "EXPOSURE"
        severity = "MEDIUM"
        strength = "LITERAL_CONFIG"

    needle = "scripts/" if "bundled_scripts_directory" in hints else "```"
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Skill references or bundles executable script content.",
        ctx=ctx,
        status="OBSERVED",
        needle=needle,
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-001",
        title="Skill references executable scripts",
        severity=severity,
        confidence="POTENTIAL",
        description=(
            f"Skill `{_label(component)}` references scripts or a bundled scripts "
            "directory. This establishes an execution *capability*; host inheritance and "
            "approval enforcement remain unverified."
        ),
        component=component,
        evidence=ev,
        capabilities=["execute_commands"],
        attacker_control="Malicious or compromised skill instructions / scripts",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Agent instruction surface → host execution",
        impact="Potential local command execution under the host agent identity",
        missing_controls=[
            "Independent approval for script execution",
            "Host effective environment / secret inheritance",
        ],
        recommended_action=(
            "Treat as an authority surface: verify whether scripts inherit sensitive "
            "environment variables and whether execution requires independent approval."
        ),
        finding_class=finding_class,
        evidence_strength=strength,
        verify_in_60s="ls the skill directory; confirm whether scripts/ is present and executed.",
    )


def rule_mcp_local_command(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "MCP Server Registration":
        return
    hints = set(component.get("priority_hints") or [])
    if "local_command_transport" not in hints and not component.get("command"):
        return

    inherits_env = "inherits_or_sets_environment" in hints
    broad_args = "broad_or_relative_path_args" in hints
    sets_env_only = "sets_environment" in hints and not inherits_env

    # Local process alone = capability. Escalate only with exposure conditions.
    # Mere presence of an `env` block (LOG_LEVEL, NODE_ENV, …) stays INFORMATIONAL.
    if inherits_env:
        finding_class: FindingClass = "SECURITY_FINDING"
        severity: Severity = "HIGH"
        confidence: VerificationStatus = "POTENTIAL"
        title = "MCP local command may inherit host credentials"
        exposure = "HOST_ENV_INHERITANCE"
        strength: EvidenceStrength = "INFERRED_HINT"
    elif broad_args:
        finding_class = "SECURITY_FINDING"
        severity = "HIGH"
        confidence = "OBSERVED"
        title = "MCP local command with broad filesystem arguments"
        exposure = "BROAD_PATH_ARGS"
        strength = "LITERAL_CONFIG"
    else:
        finding_class = "CAPABILITY"
        severity = "INFORMATIONAL"
        confidence = "OBSERVED"
        title = "MCP server launched via local command"
        exposure = "REPO_CONFIG"
        strength = "LITERAL_CONFIG"
        if sets_env_only:
            title = "MCP local command sets non-secret environment"

    command = str(component.get("command") or "")
    needle = command or None
    if broad_args and isinstance(component.get("args"), list):
        for arg in component.get("args") or []:
            arg_s = str(arg)
            if arg_s in {"/", "~"} or arg_s.startswith("~/") or ".." in arg_s:
                needle = arg_s
                break
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary=f"MCP registration launches local command `{command}`.",
        ctx=ctx,
        status="OBSERVED",
        needle=needle,
    )
    caps = ["execute_commands", "invoke_tools"]
    if inherits_env:
        caps.append("access_secrets")
    if broad_args:
        caps.append("read_files")

    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-002",
        title=title,
        severity=severity,
        confidence=confidence,
        description=(
            f"MCP server `{_label(component)}` is registered with a local command "
            "transport. "
            + (
                "Credential-shaped environment inheritance or broad path arguments "
                "elevate this beyond a simple capability observation."
                if inherits_env or broad_args
                else "Presence of a local process is a capability observation, not proof of abuse."
            )
        ),
        component=component,
        evidence=ev,
        capabilities=caps,
        attacker_control="Compromised MCP server binary/package or tool-poisoned metadata",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Host agent → MCP child process",
        impact="Tool calls execute under the MCP process identity with host-granted access",
        missing_controls=[
            "Exact artifact digest of the launched binary/package",
            "Host-side authorization binding for tool arguments",
            *(["Verified restriction of inherited environment / secrets"] if inherits_env else []),
            *(["Least-privilege filesystem binding"] if broad_args else []),
        ],
        recommended_action=(
            "Pin and verify the exact MCP server artifact, restrict env inheritance, "
            "and require approval for high-impact tools."
            if inherits_env or broad_args
            else "Record as an execution capability; verify host isolation before treating as risk."
        ),
        finding_class=finding_class,
        exposure=exposure,
        evidence_strength=strength,
        verify_in_60s=f"Open the MCP config and inspect command=`{command}` plus env/args.",
        fix_snippet="Pin the MCP binary/package; drop broad path args; avoid inheriting secrets.",
    )


def rule_mcp_remote_endpoint(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "MCP Server Registration":
        return
    if "remote_endpoint" not in set(component.get("priority_hints") or []) and not component.get(
        "url"
    ):
        return
    url = str(component.get("url") or "")
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary=f"MCP registration points at remote URL `{url}`.",
        ctx=ctx,
        status="OBSERVED",
        needle=url or None,
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-003",
        title="MCP server uses remote endpoint",
        severity="MEDIUM",
        confidence="OBSERVED",
        description=(
            f"MCP server `{_label(component)}` is configured with a remote URL. "
            "This is an external exposure surface; TLS identity and credential forwarding "
            "are not verified by this rule."
        ),
        component=component,
        evidence=ev,
        capabilities=["access_network", "invoke_tools"],
        attacker_control="Compromised remote MCP endpoint or MITM without transport identity",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Host agent → remote network service",
        impact="Potential exfiltration or tool abuse via remote MCP",
        missing_controls=[
            "Transport identity / TLS pinning",
            "OAuth / credential forwarding scope review",
        ],
        recommended_action=(
            "Verify endpoint identity, TLS, OAuth scopes, and whether secrets are forwarded."
        ),
        finding_class="EXPOSURE",
        exposure="REMOTE_ENDPOINT",
    )


def rule_hook_execution_boundary(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "Hook":
        return
    hints = set(component.get("priority_hints") or [])
    if "possible_execution_boundary" not in hints and "pre_execution_lifecycle" not in hints:
        return
    pre_tool = "pre_execution_lifecycle" in hints
    finding_class: FindingClass = "SECURITY_FINDING" if pre_tool else "CAPABILITY"
    severity: Severity = "MEDIUM" if pre_tool else "INFORMATIONAL"
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Hook configuration indicates execution or pre-tool lifecycle involvement.",
        ctx=ctx,
        status="OBSERVED",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-004",
        title="Hook can intercept or execute around tool use",
        severity=severity,
        confidence="POTENTIAL",
        description=(
            f"Hook `{_label(component)}` appears to participate in execution or "
            "pre-tool lifecycle events. Presence alone is not privilege abuse; "
            "post-approval argument mutation requires verification."
        ),
        component=component,
        evidence=ev,
        capabilities=["execute_commands", "modify_approvals"],
        attacker_control="Malicious hook definition or poisoned hook input",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="User approval → hook mutation → tool execution",
        impact="Approved actions may be altered; privileged commands may run unexpectedly",
        missing_controls=[
            "Argument integrity binding after approval",
            "Hook execution identity isolation",
        ],
        recommended_action=(
            "Confirm whether hooks can mutate tool arguments after approval and what "
            "identity they run as."
        ),
        finding_class=finding_class,
    )


def rule_skill_external_url(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "Skill":
        return
    if "external_url_reference" not in set(component.get("priority_hints") or []):
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Skill instructions reference external HTTP(S) URLs.",
        ctx=ctx,
        status="OBSERVED",
        needle="https://",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-005",
        title="Skill references external URLs",
        severity="LOW",
        confidence="OBSERVED",
        description=(
            f"Skill `{_label(component)}` references external URLs. A URL is an "
            "exposure indicator, not proof of malicious content."
        ),
        component=component,
        evidence=ev,
        capabilities=["access_network", "modify_agent_instructions"],
        attacker_control="Compromised remote resource referenced by the skill",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Reviewed skill → unreviewed remote content",
        impact="Potential instruction injection or data exfiltration guidance",
        missing_controls=["Pinned remote content digests", "Egress policy for agent fetches"],
        recommended_action="Pin or vendor remote references; treat remote content as untrusted.",
        finding_class="EXPOSURE",
        exposure="EXTERNAL_URL",
    )


def rule_skill_secrets_handling(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "Skill":
        return
    hints = set(component.get("priority_hints") or [])
    if "secrets_or_credential_handling" not in hints and "identity_or_auth_workflow" not in hints:
        return
    # Bag-of-words alone is inventory. Gate only with executable evidence.
    has_exec = "executable_evidence" in hints
    if has_exec:
        finding_class: FindingClass = "SECURITY_FINDING"
        severity: Severity = "MEDIUM"
        strength: EvidenceStrength = "INFERRED_HINT"
    else:
        finding_class = "CAPABILITY"
        severity = "LOW"
        strength = "INFERRED_HINT"
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Skill text references secrets, credentials, or identity workflows.",
        ctx=ctx,
        status="OBSERVED",
        needle="api_key" if "secrets_or_credential_handling" in hints else "service_account",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-006",
        title="Skill references secrets or identity workflows",
        severity=severity,
        confidence="POTENTIAL",
        description=(
            f"Skill `{_label(component)}` discusses secrets or authentication workflows. "
            + (
                "Executable evidence nearby elevates this beyond wording-only inventory."
                if has_exec
                else "Wording alone is inventory; confirm live credential access before gating."
            )
        ),
        component=component,
        evidence=ev,
        capabilities=["access_secrets"],
        attacker_control="Prompt injection causing the agent to follow credential-handling steps",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Agent context → credential stores / identity tooling",
        impact="Potential credential disclosure or misuse",
        missing_controls=["Secret redaction", "Separate credential broker with least privilege"],
        recommended_action="Ensure skills cannot print or forward live secrets; prefer brokers.",
        finding_class=finding_class,
        evidence_strength=strength,
    )


def rule_unattended_automation(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    ctype = str(component.get("type") or "")
    if ctype not in {
        "Automation",
        "Automation / Workflow",
        "CI Workflow",
        "Workflow",
    }:
        return
    hints = set(component.get("priority_hints") or [])
    # Ordinary CI (even with secrets.*) is inventory — not a gated authority issue.
    # Escalate only when the workflow itself grants agent/MCP-related authority
    # (RULE-016 still covers pull_request_target + agent as the high-signal case).
    agent_authority_hints = {
        "agent_related_step",
        "pull_request_target_with_agent",
        "mcp_or_agent_ci_step",
    }
    secret_hints = {
        "secrets_or_credential_handling",
        "inherits_or_sets_environment",
        "secret_reference",
        "credential_reference",
    }
    if hints.intersection(agent_authority_hints):
        finding_class: FindingClass = "SECURITY_FINDING"
        severity: Severity = "MEDIUM"
        description = (
            f"`{_label(component)}` is unattended CI that also references agent/MCP-related "
            "steps. Review triggers, tokens, and whether agent authority can run unattended."
        )
        recommended = (
            "Confirm agent/MCP steps need this workflow; pin launchers; least-privilege tokens."
        )
        caps = ["unattended_operation", "access_secrets", "invoke_agent_tooling"]
    else:
        # Presence (and even secrets in normal publish/test CI) stays CAPABILITY.
        finding_class = "CAPABILITY"
        severity = "INFORMATIONAL"
        secret_note = (
            " Secret references were observed; that alone is not a gated finding."
            if hints.intersection(secret_hints)
            else ""
        )
        description = (
            f"`{_label(component)}` is an unattended automation/CI surface.{secret_note} "
            "Legitimate automation can be secure; treat as inventory unless agent authority "
            "is introduced (see RULE-016 for privileged PR + agent)."
        )
        recommended = (
            "No gate action for ordinary CI. Review only if this workflow adds agent/MCP authority."
        )
        caps = ["unattended_operation"]
        if hints.intersection(secret_hints):
            caps.append("access_secrets")
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Unattended workflow/automation surface discovered.",
        ctx=ctx,
        status="OBSERVED",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-007",
        title="Unattended automation or CI workflow present",
        severity=severity,
        confidence="OBSERVED",
        description=description,
        component=component,
        evidence=ev,
        capabilities=caps,
        attacker_control="Malicious trigger payload or compromised workflow definition",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Trigger → privileged unattended execution",
        impact="Actions may run without interactive human approval",
        missing_controls=[
            "Webhook authentication / replay protection",
            "Least-privilege workflow tokens",
        ],
        recommended_action=recommended,
        finding_class=finding_class,
    )


def rule_subagent_delegation(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "Subagent":
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Subagent definition discovered; delegated authority not verified.",
        ctx=ctx,
        status="OBSERVED",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-008",
        title="Subagent may inherit delegated authority",
        severity="INFORMATIONAL",
        confidence="POTENTIAL",
        description=(
            f"Subagent `{_label(component)}` can receive delegated tasks. "
            "Delegation alone is not a security defect; verify privilege reduction and isolation."
        ),
        component=component,
        evidence=ev,
        capabilities=["delegate_tasks"],
        attacker_control="Compromised parent agent or poisoned delegated task content",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Parent agent → subagent",
        impact="Excessive authority or cross-tenant data exposure via delegation",
        missing_controls=["Privilege reduction on delegate", "Inter-agent message authentication"],
        recommended_action="Verify inherited credentials, tool allowlists, and memory isolation.",
        finding_class="CAPABILITY",
    )


def rule_example_mcp_config(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "MCP Server Registration":
        return
    if "example_or_template_config" not in set(component.get("priority_hints") or []):
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="MCP registration appears to be an example/template configuration.",
        ctx=ctx,
        status="OBSERVED",
        limitations=["May not be loaded by the host; still a configuration surface to review."],
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-009",
        title="Example MCP config may be mistaken for production registration",
        severity="LOW",
        confidence="OBSERVED",
        description=(
            f"MCP registration `{_label(component)}` looks like an example/template. "
            "Confirm it is not loaded by the host agent in production."
        ),
        component=component,
        evidence=ev,
        capabilities=["invoke_tools"],
        attacker_control="Accidental promotion of example config into a live host",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Documentation/example → live agent configuration",
        impact="Unexpected tool surface if example configs are installed",
        missing_controls=["Host config allowlist excluding examples"],
        recommended_action="Ensure example configs are not on the host's MCP search path.",
        finding_class="EXPOSURE",
    )


def rule_instruction_injection_markers(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    """Flag skills/rules with injection-oriented name markers or abuse-shaped content.

    NAME_MARKER hits stay CAPABILITY/LOW. Content-based
    ``instruction_abuse_content`` escalates to EXPOSURE/MEDIUM with INFERRED_HINT.
    """
    ctype = str(component.get("type") or "")
    if ctype not in {"Skill", "Rule pack"}:
        return
    hints = set(component.get("priority_hints") or [])
    path = str(component.get("repository_path") or "").lower()
    name = str(component.get("name") or "").lower()
    markers = ("injection", "exfil", "ignore previous", "jailbreak")
    name_hit = any(m in path or m in name for m in markers)
    content_hit = "instruction_abuse_content" in hints
    if not name_hit and not content_hit:
        return

    if content_hit:
        strength: EvidenceStrength = "INFERRED_HINT"
        finding_class: FindingClass = "EXPOSURE"
        severity: Severity = "MEDIUM"
        confidence: VerificationStatus = "OBSERVED"
        summary = "Instruction text contains hide/bypass/fetch-execute style directives."
        title = "Instruction text directs hide, bypass, or fetch-execute behavior"
        description = (
            f"`{_label(component)}` contains instruction patterns that hide actions, "
            "bypass confirmation, or fetch-and-execute remote content. Review before trusting."
        )
        recommended = "Rewrite instructions; forbid hide/bypass/remote-exec directives in skills."
        verify = "Search the SKILL.md for hide/bypass/fetch-and-execute phrasing."
    else:
        strength = "NAME_MARKER"
        finding_class = "CAPABILITY"
        severity = "LOW"
        confidence = "POTENTIAL"
        summary = "Component path/name suggests prompt-injection oriented content."
        title = "Potential prompt-injection oriented instruction surface"
        description = (
            f"`{_label(component)}` appears related to prompt-injection patterns by "
            "name/path. Naming alone is a weak signal — treat as triage, not confirmed abuse."
        )
        recommended = "Review full instruction text; do not auto-activate in privileged hosts."
        verify = "Open the file; naming alone is weak — read the instruction text."

    ev = build_rule_evidence(
        evidences,
        component=component,
        summary=summary,
        ctx=ctx,
        status="OBSERVED" if content_hit else "POTENTIAL",
        limitations=[
            "Content markers are heuristic; confirm intent before treating as malicious.",
        ],
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-010",
        title=title,
        severity=severity,
        confidence=confidence,
        description=description,
        component=component,
        evidence=ev,
        capabilities=["modify_agent_instructions"],
        attacker_control="Instruction content in the component itself",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Untrusted instructions → privileged agent tools",
        impact="Agent may follow injected instructions leading to privileged actions",
        missing_controls=["Instruction isolation", "Tool allowlists for untrusted content"],
        recommended_action=recommended,
        finding_class=finding_class,
        evidence_strength=strength,
        verify_in_60s=verify,
    )


def rule_permission_bypass_flag(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if "permission_bypass_flag" not in set(component.get("priority_hints") or []):
        return
    ctype = str(component.get("type") or "")
    if ctype not in {
        "Skill",
        "Hook",
        "MCP Server Registration",
        "CI Workflow",
        "Automation",
        "Host Settings",
    }:
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Component references a permission-bypass or auto-approve flag.",
        ctx=ctx,
        status="OBSERVED",
        needle="skip-permissions",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-017",
        title="Permission-bypass or auto-approve flag in agent surface",
        severity="HIGH",
        confidence="OBSERVED",
        description=(
            f"`{_label(component)}` references a flag that disables human approval "
            "(e.g. `--dangerously-skip-permissions`, `--yolo`, auto-approve). That expands "
            "effective authority without a corresponding control."
        ),
        component=component,
        evidence=ev,
        capabilities=["modify_approvals", "execute_commands", "unattended_operation"],
        attacker_control="Anyone who can influence the command/config that sets the flag",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Human approval gate → bypassed automated agent",
        impact="Privileged tool use without interactive confirmation",
        missing_controls=["Require approval for high-impact tools", "Disallow bypass flags in CI"],
        recommended_action="Remove bypass flags; keep approval required for privileged actions.",
        finding_class="SECURITY_FINDING",
        exposure="PERMISSION_BYPASS",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="grep for dangerously-skip-permissions / yolo / autoApprove / bypass.",
        fix_snippet="Delete the bypass flag; keep interactive or policy-gated approvals.",
    )


def rule_unpinned_package_launcher(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "MCP Server Registration":
        return
    if "unpinned_package_launcher" not in set(component.get("priority_hints") or []):
        return
    command = str(component.get("command") or "")
    args = component.get("args") or []
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary=f"MCP launcher `{command}` appears unpinned (npx -y / uvx / similar).",
        ctx=ctx,
        status="OBSERVED",
        needle=command or "npx",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-011",
        title="MCP server launched via unpinned package installer",
        severity="HIGH",
        confidence="OBSERVED",
        description=(
            f"MCP server `{_label(component)}` uses an unpinned launcher "
            f"(`{command}` {' '.join(str(a) for a in args)}). A later package publish can "
            "change behavior without a config edit (rug-pull risk)."
        ),
        component=component,
        evidence=ev,
        capabilities=["execute_commands", "invoke_tools"],
        attacker_control="Malicious or compromised package published to the unpinned name",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Host agent → package registry → MCP process",
        impact="Arbitrary code execution under the host agent identity after a registry update",
        missing_controls=["Pinned version or content digest", "Allowlisted package source"],
        recommended_action="Pin an exact version or digest; avoid `npx -y` / floating `uvx` tags.",
        finding_class="SECURITY_FINDING",
        exposure="UNPINNED_LAUNCHER",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="grep the MCP JSON for npx -y / uvx and confirm no @version pin.",
        fix_snippet='Use "command": "npx", "args": ["-y", "pkg@1.2.3"] or a local pinned binary.',
    )


def rule_literal_secret_in_mcp_env(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "MCP Server Registration":
        return
    hints = set(component.get("priority_hints") or [])
    severity: Severity
    strength: EvidenceStrength
    if "literal_secret_in_env" in hints:
        severity = "CRITICAL"
        title = "Literal secret-like value in MCP env"
        strength = "LITERAL_CONFIG"
        description = (
            f"MCP server `{_label(component)}` appears to embed a literal credential in "
            "`env` rather than a placeholder reference. Committed secrets are an immediate "
            "exposure."
        )
    elif "literal_secret_like_placeholder" in hints:
        severity = "MEDIUM"
        title = "Possible template/placeholder secret-like MCP env value"
        strength = "INFERRED_HINT"
        description = (
            f"MCP server `{_label(component)}` has a secret-named env value that looks like "
            "a template placeholder (for example `your-api-key-here`), not a known token format. "
            "Confirm it is not a real credential before dismissing."
        )
    else:
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="MCP registration embeds a literal secret-like value in env.",
        ctx=ctx,
        status="OBSERVED",
        needle="env",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-012",
        title=title,
        severity=severity,
        confidence="OBSERVED",
        description=description,
        component=component,
        evidence=ev,
        capabilities=["access_secrets"],
        attacker_control="Anyone with repo or backup access can read the credential",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Repository contents → MCP process environment",
        impact="Credential theft and downstream account takeover",
        missing_controls=["Secret store / OS keychain", "Placeholder env expansion only"],
        recommended_action="Replace literal values with `${ENV}` references; rotate the secret.",
        finding_class="SECURITY_FINDING",
        exposure="LITERAL_SECRET",
        evidence_strength=strength,
        verify_in_60s="Open the MCP JSON env block; confirm values are placeholders, not literals.",
        fix_snippet='Use "API_KEY": "${API_KEY}" and inject from the host secret store.',
    )


def rule_insecure_http_remote_mcp(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "MCP Server Registration":
        return
    if "insecure_http_remote" not in set(component.get("priority_hints") or []):
        return
    url = str(component.get("url") or "")
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary=f"MCP remote endpoint uses cleartext HTTP: `{url}`.",
        ctx=ctx,
        status="OBSERVED",
        needle="http://",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-013",
        title="Remote MCP endpoint uses cleartext HTTP",
        severity="HIGH",
        confidence="OBSERVED",
        description=(
            f"MCP server `{_label(component)}` points at `{url}` over HTTP. Tool traffic "
            "and any forwarded credentials lack transport confidentiality/integrity."
        ),
        component=component,
        evidence=ev,
        capabilities=["access_network", "invoke_tools", "access_secrets"],
        attacker_control="Network MITM on the path to the MCP endpoint",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Host agent → cleartext network → remote MCP",
        impact="Credential and tool-argument interception or modification",
        missing_controls=["HTTPS / TLS", "Certificate pinning where appropriate"],
        recommended_action="Use https:// only; reject plain HTTP remote MCP registrations.",
        finding_class="SECURITY_FINDING",
        exposure="INSECURE_TRANSPORT",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="Confirm the url field starts with https://.",
        fix_snippet='Change "url": "http://..." to "https://...".',
    )


def rule_hidden_unicode_instructions(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") not in {
        "Skill",
        "Rule / instruction file",
        "Rule pack",
    }:
        return
    if "hidden_unicode_in_instructions" not in set(component.get("priority_hints") or []):
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Instruction text contains hidden/bidi Unicode code points.",
        ctx=ctx,
        status="OBSERVED",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-014",
        title="Hidden or bidi Unicode in agent instructions",
        severity="HIGH",
        confidence="OBSERVED",
        description=(
            f"`{_label(component)}` contains zero-width or bidirectional Unicode "
            "characters that can hide or reorder instructions to humans while remaining "
            "visible to the model."
        ),
        component=component,
        evidence=ev,
        capabilities=["modify_agent_instructions"],
        attacker_control="Author of the instruction / rules file",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Human review → Unicode-obscured model instructions",
        impact="Covert instruction injection past visual review",
        missing_controls=["Unicode normalization / disallowlist on ingest"],
        recommended_action="Strip bidi/zero-width characters; re-review the visible text.",
        finding_class="SECURITY_FINDING",
        exposure="HIDDEN_UNICODE",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="hexdump or `python -c` for U+200B/U+202E in the SKILL.md bytes.",
        fix_snippet="Remove zero-width and bidi override characters from the file.",
    )


def rule_download_and_execute(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    ctype = str(component.get("type") or "")
    if ctype not in {"Skill", "Hook", "MCP Server Registration", "Host Settings"}:
        return
    if "download_and_execute" not in set(component.get("priority_hints") or []):
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Component text references download-and-execute patterns (curl|sh / similar).",
        ctx=ctx,
        status="OBSERVED",
        needle="curl",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-015",
        title="Download-and-execute pattern in agent surface",
        severity="CRITICAL",
        confidence="OBSERVED",
        description=(
            f"`{_label(component)}` references piping a remote download into a shell. "
            "That is remote code execution under the agent/host identity if followed."
        ),
        component=component,
        evidence=ev,
        capabilities=["execute_commands", "access_network"],
        attacker_control="Remote URL content at fetch time",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Reviewed instructions → unreviewed remote script",
        impact="Arbitrary remote code execution",
        missing_controls=["Pinned script digest", "No pipe-to-shell in agent surfaces"],
        recommended_action="Vendor and pin scripts; never curl|sh from skills or hooks.",
        finding_class="SECURITY_FINDING",
        exposure="DOWNLOAD_EXEC",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="Search the file for `curl .*|` / `wget .*|` / `iwr .*| iex`.",
        fix_snippet="Replace with a pinned local script checked into the repo.",
    )


def rule_project_mcp_auto_approve(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "Host Settings":
        return
    if "project_mcp_auto_approve" not in set(component.get("priority_hints") or []):
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Host settings enable auto-approval of all project MCP servers.",
        ctx=ctx,
        status="OBSERVED",
        needle="enableAllProjectMcpServers",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-018",
        title="Project MCP servers auto-approved",
        severity="HIGH",
        confidence="OBSERVED",
        description=(
            f"`{_label(component)}` sets `enableAllProjectMcpServers`, so every MCP "
            "server declared in the project's `.mcp.json` runs without a trust prompt."
        ),
        component=component,
        evidence=ev,
        capabilities=["invoke_tools", "execute_commands", "modify_approvals"],
        attacker_control="Anyone who can commit project MCP config",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Repo-controlled MCP registration → auto-approved tools",
        impact="Unreviewed MCP servers gain tool authority on project open",
        missing_controls=["Per-server trust prompt", "CODEOWNERS on .mcp.json / settings"],
        recommended_action="Set enableAllProjectMcpServers to false; approve servers individually.",
        finding_class="SECURITY_FINDING",
        exposure="MCP_AUTO_APPROVE",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="Open .claude/settings.json and check enableAllProjectMcpServers.",
        fix_snippet='"enableAllProjectMcpServers": false',
    )


def rule_base_url_or_proxy_override(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    ctype = str(component.get("type") or "")
    if ctype not in {"Host Settings", "MCP Server Registration"}:
        return
    if "base_url_or_proxy_override" not in set(component.get("priority_hints") or []):
        return
    detail = component.get("settings_detail") or component.get("mcp_detail") or {}
    key = str(detail.get("override_key") or "ANTHROPIC_BASE_URL")
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary=f"Host settings override model/API routing via `{key}`.",
        ctx=ctx,
        status="OBSERVED",
        needle=key,
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-019",
        title="Base-URL or proxy override in project settings",
        severity="HIGH",
        confidence="OBSERVED",
        description=(
            f"`{_label(component)}` sets `{key}` in configuration env. That can redirect "
            "model traffic (and prompts/secrets in-flight) to an attacker-controlled endpoint."
        ),
        component=component,
        evidence=ev,
        capabilities=["access_network", "access_secrets", "modify_agent_instructions"],
        attacker_control="Anyone who can edit project settings / env",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Repo-controlled env → model provider routing",
        impact="Prompt and credential interception via rogue API base URL or proxy",
        missing_controls=["Disallow project base-URL overrides", "Pin provider endpoints"],
        recommended_action=f"Remove `{key}` from project settings; keep provider URL host-controlled.",
        finding_class="SECURITY_FINDING",
        exposure="BASE_URL_OVERRIDE",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s=f"grep {key} in .claude/settings.json / project env.",
        fix_snippet=f"Delete the `{key}` entry from project env.",
    )


def rule_pull_request_target_with_agent(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    if component.get("type") != "CI Workflow":
        return
    hints = set(component.get("priority_hints") or [])
    if "pull_request_target_with_agent" not in hints:
        return
    if "workflow_mitigation_present" in hints:
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Workflow combines pull_request_target with agent/MCP-related steps.",
        ctx=ctx,
        status="OBSERVED",
        needle="pull_request_target",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-016",
        title="pull_request_target workflow invokes agent-related steps",
        severity="HIGH",
        confidence="OBSERVED",
        description=(
            f"CI workflow `{_label(component)}` uses `pull_request_target` together with "
            "observed agent/MCP steps (`uses:` or launcher CLI). Fork PRs can often influence "
            "checkout/content while retaining privileged secrets — a classic CI + agent abuse path."
        ),
        component=component,
        evidence=ev,
        capabilities=["unattended_operation", "access_secrets", "execute_commands"],
        attacker_control="Malicious pull request from a fork",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Fork PR content → privileged workflow + agent tools",
        impact="Secret theft or privileged agent actions from untrusted PR content",
        missing_controls=[
            "Avoid pull_request_target for untrusted code",
            "Persist-credentials false + explicit safe checkout",
        ],
        recommended_action="Prefer pull_request; never feed fork PR code to privileged agents.",
        finding_class="SECURITY_FINDING",
        exposure="PR_TARGET_AGENT",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="Confirm `on: pull_request_target` and whether agent steps touch PR code.",
        fix_snippet="Switch to pull_request, or isolate secrets from any PR-controlled checkout.",
    )


def _typosquat_candidate(component: dict[str, Any]) -> str | None:
    ctype = str(component.get("type") or "")
    if ctype == "Skill":
        return str(component.get("name") or "") or None
    if ctype != "MCP Server Registration":
        return None
    args = component.get("args")
    if isinstance(args, list):
        for arg in args:
            text = str(arg)
            if text.startswith("@") or (text.count("/") == 1 and not text.startswith(".")):
                return text
    return str(component.get("name") or "") or None


def rule_typosquat_known_name(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    """AUTHDIFF-RULE-020 — near-match to a shipped list of known skill/MCP names.

    Incident class: typosquat / social-engineering install (ClawHavoc-style).
    Evidence is NAME proximity only → never CRITICAL; does not gate alone via
    NAME_MARKER exclusion in gating.
    """
    from authdiff.typosquat import nearest_typosquat

    candidate = _typosquat_candidate(component)
    if not candidate:
        return
    hit = nearest_typosquat(candidate, max_distance=2)
    if hit is None:
        return
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary=(
            f"Name `{hit['candidate']}` is within edit distance {hit['distance']} "
            f"of known `{hit['known']}`."
        ),
        ctx=ctx,
        status="POTENTIAL",
        needle=str(hit["candidate"]),
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-020",
        title="Possible typosquat of a known agent component name",
        severity="MEDIUM",
        confidence="POTENTIAL",
        description=(
            f"`{_label(component)}` looks similar to known component `{hit['known']}` "
            f"(edit distance {hit['distance']}). Typosquat campaigns often rely on "
            "near-identical names plus install instructions — verify publisher identity."
        ),
        component=component,
        evidence=ev,
        capabilities=["invoke_tools", "execute_commands"],
        attacker_control="Typosquat package or skill published under a lookalike name",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Install instruction / registry name → host agent tools",
        impact="Malicious skill or MCP server installed in place of a well-known one",
        missing_controls=[
            "Pin exact package name + version/digest",
            "Verify publisher / registry provenance",
        ],
        recommended_action=(
            f"Confirm the name is intentional (not `{hit['known']}`); pin version; "
            "vet with `authdiff open` before install."
        ),
        finding_class="EXPOSURE",
        exposure="TYPOSQUAT_NAME",
        evidence_strength="NAME_MARKER",
        verify_in_60s=f"Diff the spelling against `{hit['known']}` and check the publisher.",
        fix_snippet=f"Use the canonical name `{hit['known']}` (pinned), or document why not.",
    )


def rule_unpinned_with_secrets_combo(
    component: dict[str, Any],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    """AUTHDIFF-RULE-021 — unpinned launcher combined with literal MCP env secrets."""
    if component.get("type") != "MCP Server Registration":
        return
    hints = set(component.get("priority_hints") or [])
    if "unpinned_package_launcher" not in hints:
        return
    if "literal_secret_in_env" not in hints and "literal_secret_like_placeholder" not in hints:
        return
    critical = "literal_secret_in_env" in hints
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Unpinned MCP launcher combined with secret-like env values.",
        ctx=ctx,
        status="OBSERVED",
        needle=str(component.get("command") or "npx"),
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-021",
        title="Unpinned MCP launcher with secret-bearing env",
        severity="CRITICAL" if critical else "HIGH",
        confidence="OBSERVED" if critical else "POTENTIAL",
        description=(
            f"MCP server `{_label(component)}` combines an unpinned package launcher with "
            "secret-like environment values. A registry rug-pull can inherit those secrets "
            "without a config change."
        ),
        component=component,
        evidence=ev,
        capabilities=["execute_commands", "access_secrets", "invoke_tools"],
        attacker_control="Compromised registry package + embedded or inherited credentials",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Package registry → MCP process env → secret material",
        impact="Credential theft or privileged tool abuse after an unpinned update",
        missing_controls=[
            "Pinned package version/digest",
            "Env placeholders only (no literals)",
        ],
        recommended_action="Pin the package and replace env literals with ${ENV} references.",
        finding_class="SECURITY_FINDING",
        exposure="UNPINNED_WITH_SECRETS",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="Confirm npx -y/uvx without pin AND secret-named env keys in the same server.",
        fix_snippet='Pin pkg@1.2.3; set "API_KEY": "${API_KEY}" (not a literal).',
    )


def apply_cross_component_rules(
    components: list[dict[str, Any]],
    evidences: list[Evidence],
    findings: list[Finding],
    ctx: EvidenceContext,
) -> None:
    """AUTHDIFF-RULE-022 — permission bypass + project MCP auto-approve in one tree."""
    bypass = [
        c for c in components if "permission_bypass_flag" in set(c.get("priority_hints") or [])
    ]
    auto = [
        c for c in components if "project_mcp_auto_approve" in set(c.get("priority_hints") or [])
    ]
    if not bypass or not auto:
        return
    component = auto[0]
    ev = build_rule_evidence(
        evidences,
        component=component,
        summary="Project MCP auto-approve co-occurs with a permission-bypass flag.",
        ctx=ctx,
        status="OBSERVED",
        needle="enableAllProjectMcpServers",
    )
    _add_finding(
        findings,
        rule_id="AUTHDIFF-RULE-022",
        title="Permission bypass combined with project MCP auto-approve",
        severity="CRITICAL",
        confidence="OBSERVED",
        description=(
            "This repository both disables human approval gates "
            f"(`{_label(bypass[0])}`) and auto-approves project MCP servers "
            f"(`{_label(component)}`). Together they remove the two main "
            "authority checkpoints hosts rely on."
        ),
        component=component,
        evidence=ev,
        capabilities=[
            "modify_approvals",
            "invoke_tools",
            "execute_commands",
            "unattended_operation",
        ],
        attacker_control="Poisoned project MCP + bypassed host approval",
        entry_point=str(component.get("repository_path") or ""),
        trust_boundary="Project settings → host agent without approval prompts",
        impact="Untrusted MCP tools can run with reduced or no human gates",
        missing_controls=[
            "Remove permission-bypass flags",
            "Disable enableAllProjectMcpServers",
        ],
        recommended_action="Remove bypass flags and require per-server MCP approval.",
        finding_class="SECURITY_FINDING",
        exposure="BYPASS_WITH_MCP_AUTO",
        evidence_strength="LITERAL_CONFIG",
        verify_in_60s="Confirm both a bypass flag and enableAllProjectMcpServers=true exist.",
        fix_snippet='Delete bypass flags; set "enableAllProjectMcpServers": false.',
    )


RULES: list[RuleSpec] = [
    RuleSpec(
        "AUTHDIFF-RULE-001",
        "Skill references executable scripts",
        "1.2",
        rule_skill_bundled_scripts,
    ),
    RuleSpec("AUTHDIFF-RULE-002", "MCP local command transport", "1.2", rule_mcp_local_command),
    RuleSpec("AUTHDIFF-RULE-003", "MCP remote endpoint", "1.2", rule_mcp_remote_endpoint),
    RuleSpec("AUTHDIFF-RULE-004", "Hook execution boundary", "1.2", rule_hook_execution_boundary),
    RuleSpec("AUTHDIFF-RULE-005", "Skill external URLs", "1.2", rule_skill_external_url),
    RuleSpec("AUTHDIFF-RULE-006", "Skill secrets handling", "1.2", rule_skill_secrets_handling),
    RuleSpec("AUTHDIFF-RULE-007", "Unattended automation", "1.3", rule_unattended_automation),
    RuleSpec("AUTHDIFF-RULE-008", "Subagent delegation", "1.2", rule_subagent_delegation),
    RuleSpec("AUTHDIFF-RULE-009", "Example MCP config", "1.2", rule_example_mcp_config),
    RuleSpec(
        "AUTHDIFF-RULE-010",
        "Prompt-injection oriented surface",
        "1.2",
        rule_instruction_injection_markers,
    ),
    RuleSpec(
        "AUTHDIFF-RULE-011", "Unpinned MCP package launcher", "1.0", rule_unpinned_package_launcher
    ),
    RuleSpec(
        "AUTHDIFF-RULE-012", "Literal secret in MCP env", "1.0", rule_literal_secret_in_mcp_env
    ),
    RuleSpec(
        "AUTHDIFF-RULE-013", "Cleartext HTTP remote MCP", "1.0", rule_insecure_http_remote_mcp
    ),
    RuleSpec(
        "AUTHDIFF-RULE-014",
        "Hidden Unicode in instructions",
        "1.0",
        rule_hidden_unicode_instructions,
    ),
    RuleSpec("AUTHDIFF-RULE-015", "Download-and-execute pattern", "1.0", rule_download_and_execute),
    RuleSpec(
        "AUTHDIFF-RULE-016",
        "pull_request_target with agent steps",
        "1.0",
        rule_pull_request_target_with_agent,
    ),
    RuleSpec(
        "AUTHDIFF-RULE-017",
        "Permission-bypass / auto-approve flag",
        "1.0",
        rule_permission_bypass_flag,
    ),
    RuleSpec("AUTHDIFF-RULE-018", "Project MCP auto-approve", "1.0", rule_project_mcp_auto_approve),
    RuleSpec(
        "AUTHDIFF-RULE-019", "Base-URL or proxy override", "1.0", rule_base_url_or_proxy_override
    ),
    RuleSpec(
        "AUTHDIFF-RULE-020",
        "Typosquat of known component name",
        "1.0",
        rule_typosquat_known_name,
    ),
    RuleSpec(
        "AUTHDIFF-RULE-021",
        "Unpinned launcher with secrets",
        "1.0",
        rule_unpinned_with_secrets_combo,
    ),
]

# Applied after per-component RULES (see apply_cross_component_rules).
CROSS_COMPONENT_RULE_IDS: tuple[str, ...] = ("AUTHDIFF-RULE-022",)


def apply_all_rules(
    components: list[dict[str, Any]],
    *,
    ctx: EvidenceContext | None = None,
) -> tuple[list[Evidence], list[Finding]]:
    evidences: list[Evidence] = []
    findings: list[Finding] = []
    context = ctx or EvidenceContext()
    for component in components:
        for rule in RULES:
            rule.apply(component, evidences, findings, context)
    apply_cross_component_rules(components, evidences, findings, context)
    return evidences, findings
