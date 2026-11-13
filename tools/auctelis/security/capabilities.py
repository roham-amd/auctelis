"""Extract security-relevant capabilities from inventory component records.

Capability origins:
- DECLARED / POTENTIAL from configuration hints
- TYPE_DEFAULT from component type alone (never treat as effective permission)
- EFFECTIVE / VERIFIED require host or runtime evidence (not produced here)
"""

from __future__ import annotations

from typing import Any

from auctelis.security.models import (
    Capability,
    CapabilityKind,
    CapabilityOrigin,
    VerificationStatus,
)

_HINT_TO_CAPABILITY: dict[str, tuple[CapabilityKind, VerificationStatus, CapabilityOrigin]] = {
    "possible_code_execution_reference": ("execute_commands", "POTENTIAL", "POTENTIAL"),
    "script_reference": ("execute_commands", "POTENTIAL", "POTENTIAL"),
    "bundled_scripts_directory": ("execute_commands", "OBSERVED", "DECLARED"),
    "local_command_transport": ("execute_commands", "OBSERVED", "DECLARED"),
    "possible_execution_boundary": ("execute_commands", "POTENTIAL", "POTENTIAL"),
    "inherits_or_sets_environment": ("access_secrets", "POTENTIAL", "POTENTIAL"),
    "secrets_or_credential_handling": ("access_secrets", "POTENTIAL", "POTENTIAL"),
    "identity_or_auth_workflow": ("access_secrets", "POTENTIAL", "POTENTIAL"),
    "external_url_reference": ("access_network", "POTENTIAL", "POTENTIAL"),
    "remote_endpoint": ("access_network", "OBSERVED", "DECLARED"),
    "pre_execution_lifecycle": ("modify_approvals", "POTENTIAL", "POTENTIAL"),
    "mcp_server_source": ("invoke_tools", "OBSERVED", "DECLARED"),
    "broad_or_relative_path_args": ("read_files", "POTENTIAL", "POTENTIAL"),
}


_TYPE_DEFAULTS: dict[str, list[tuple[CapabilityKind, VerificationStatus, str]]] = {
    "Skill": [
        ("modify_agent_instructions", "OBSERVED", "Skills inject instructions into the agent."),
    ],
    "Hook": [
        ("unattended_operation", "POTENTIAL", "Hooks can run on lifecycle events."),
        ("modify_approvals", "POTENTIAL", "Pre-tool hooks may alter approved arguments."),
    ],
    "Automation": [
        ("unattended_operation", "OBSERVED", "Automations may run without interactive approval."),
    ],
    "CI Workflow": [
        ("unattended_operation", "OBSERVED", "CI workflows execute with repository privileges."),
        ("access_secrets", "POTENTIAL", "Workflows commonly inherit repository secrets."),
    ],
    "Workflow": [
        ("unattended_operation", "OBSERVED", "Workflows may execute without interactive approval."),
    ],
    "Subagent": [
        ("delegate_tasks", "OBSERVED", "Subagents receive delegated authority."),
    ],
    "Plugin": [
        ("invoke_tools", "POTENTIAL", "Plugins often expose additional tools."),
    ],
    "MCP Server Registration": [
        ("invoke_tools", "OBSERVED", "MCP registration exposes tool surface to the host agent."),
    ],
    "MCP Server Implementation": [
        ("invoke_tools", "OBSERVED", "MCP server source implements callable tools."),
    ],
    "A2A": [
        ("delegate_tasks", "POTENTIAL", "Agent cards advertise delegation / task surfaces."),
        ("access_network", "POTENTIAL", "A2A endpoints are network-reachable by design."),
    ],
}


def extract_capabilities(components: list[dict[str, Any]]) -> list[Capability]:
    caps: list[Capability] = []
    for comp in components:
        cid = str(comp.get("component_id") or "")
        ctype = str(comp.get("type") or "")
        hints = [str(h) for h in (comp.get("priority_hints") or [])]
        seen: set[CapabilityKind] = set()

        for hint in hints:
            mapped = _HINT_TO_CAPABILITY.get(hint)
            if not mapped:
                continue
            kind, status, origin = mapped
            if kind in seen:
                continue
            seen.add(kind)
            caps.append(
                Capability(
                    kind=kind,
                    status=status,
                    component_id=cid,
                    evidence_ids=[f"E-INV-{cid}"],
                    notes=f"Derived from priority hint `{hint}`.",
                    origin=origin,
                )
            )

        for kind, status, notes in _TYPE_DEFAULTS.get(ctype, []):
            if kind in seen:
                continue
            seen.add(kind)
            caps.append(
                Capability(
                    kind=kind,
                    status=status,
                    component_id=cid,
                    evidence_ids=[f"E-INV-{cid}"],
                    notes=notes,
                    origin="TYPE_DEFAULT",
                )
            )
    return caps


def authority_bearing_component_ids(capabilities: list[Capability]) -> set[str]:
    authority = {
        "execute_commands",
        "access_secrets",
        "access_network",
        "modify_approvals",
        "delegate_tasks",
        "unattended_operation",
    }
    return {
        c.component_id
        for c in capabilities
        if c.kind in authority and c.status in {"OBSERVED", "POTENTIAL", "CONFIRMED"}
    }
