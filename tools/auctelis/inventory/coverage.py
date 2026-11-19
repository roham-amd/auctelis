from __future__ import annotations

from typing import Any

# Normative authority layers — keep distinct in product language and artifacts.
AUTHORITY_LAYERS: dict[str, str] = {
    "DECLARED": "What the integration says it requires or exposes.",
    "CONFIGURED": "What host/repo configuration appears to expose.",
    "EFFECTIVE": "What the execution environment actually permits.",
    "VERIFIED": "What an authorized test independently established.",
}

# Maturity of deterministic discovery for each ecosystem family.
ADAPTER_COVERAGE: list[dict[str, str | None]] = [
    {
        "family": "Skill",
        "adapter": "skill_md",
        "maturity": "SUPPORTED",
        "notes": "Discovers SKILL.md manifests; does not verify runtime behavior.",
    },
    {
        "family": "MCP",
        "adapter": "mcp_config",
        "maturity": "PARTIAL",
        "notes": "Client registration JSON including mcp_example.json; effective host binding is MANUAL_ONLY.",
    },
    {
        "family": "MCP server source",
        "adapter": "mcp_server_source",
        "maturity": "PARTIAL",
        "notes": "Heuristic discovery of MCP server implementations; tool authz not verified.",
    },
    {
        "family": "A2A",
        "adapter": "a2a_agent_card",
        "maturity": "PARTIAL",
        "notes": "Agent card JSON identity; message trust and delegation are MANUAL_ONLY.",
    },
    {
        "family": "Instruction rules",
        "adapter": "instruction_rules",
        "maturity": "SUPPORTED",
        "notes": (
            "AGENTS.md, CLAUDE.md, Cursor rules pack paths, and "
            ".claude/commands/**/*.md slash-commands."
        ),
    },
    {
        "family": "Hook",
        "adapter": "hooks",
        "maturity": "PARTIAL",
        "notes": (
            "hooks.json + hooks/ layouts with lifecycle/identity hints; "
            "Claude settings hooks via claude_settings. Effective host binding MANUAL_ONLY."
        ),
    },
    {
        "family": "Plugin",
        "adapter": "plugins",
        "maturity": "PARTIAL",
        "notes": "Manifest heuristics only; publisher and OAuth scopes are MANUAL_ONLY.",
    },
    {
        "family": "Subagent",
        "adapter": "subagents",
        "maturity": "PARTIAL",
        "notes": "agents/ and subagents/ definitions; inherited permissions need deep review.",
    },
    {
        "family": "Automation",
        "adapter": "automations",
        "maturity": "PARTIAL",
        "notes": "Workflow and automation manifests; effective credentials are NOT VERIFIED.",
    },
    {
        "family": "CI / GitHub Actions",
        "adapter": "github_workflows",
        "maturity": "PARTIAL",
        "notes": "Discovers .github/workflows; does not evaluate runner trust or secret exfil paths.",
    },
    {
        "family": "Host effective permissions",
        "adapter": "host_profiles",
        "maturity": "PARTIAL",
        "notes": "Host profile markers only; effective runtime permissions stay MANUAL_ONLY.",
    },
    {
        "family": "Browser agents",
        "adapter": None,
        "maturity": "MANUAL_ONLY",
        "notes": "Assessment module exists; no dedicated discovery adapter.",
    },
    {
        "family": "Memory / RAG",
        "adapter": None,
        "maturity": "MANUAL_ONLY",
        "notes": "Assessment module exists; tenant isolation not auto-discovered.",
    },
    {
        "family": "Model providers",
        "adapter": None,
        "maturity": "MANUAL_ONLY",
        "notes": "Assessment module exists; endpoint/model config discovery not automated.",
    },
    {
        "family": "Multimodal artifacts",
        "adapter": None,
        "maturity": "MANUAL_ONLY",
        "notes": "Assessment module exists; no artifact inspection adapters.",
    },
    {
        "family": "Runtime behavior",
        "adapter": None,
        "maturity": "UNSUPPORTED",
        "notes": "No runtime harness in passive mode.",
    },
    {
        "family": "Publisher / artifact provenance",
        "adapter": None,
        "maturity": "MANUAL_ONLY",
        "notes": "Digest helpers exist; full signature/SBOM verification is not shipped.",
    },
]


_AGENT_CONFIG_MARKERS = (
    "mcp.json",
    ".mcp.json",
    "mcp_config",
    ".claude/",
    ".cursor/",
    ".vscode/mcp",
    "hooks.json",
    "settings.json",
    "skill.md",
)


def count_unparsed_agent_configs(events: list[Any] | None) -> int:
    count = 0
    for event in events or []:
        if not isinstance(event, dict):
            continue
        etype = str(event.get("type") or "")
        path = str(event.get("path") or "").replace("\\", "/").lower()
        if etype == "unparsed_agent_config":
            count += 1
            continue
        if etype in {
            "parse_error",
            "parse_skipped_size",
            "skipped_oversize",
            "file_too_large",
        } and any(marker in path for marker in _AGENT_CONFIG_MARKERS):
            count += 1
    return count


def count_truncation_events(events: list[Any] | None) -> dict[str, int]:
    """Count walk limits that silently drop inventory (depth / file / read)."""
    depth = 0
    file_limit = 0
    read_error = 0
    for event in events or []:
        if not isinstance(event, dict):
            continue
        etype = str(event.get("type") or "")
        if etype == "depth_limit":
            depth += 1
        elif etype == "file_limit_reached":
            file_limit += 1
        elif etype in {"read_error", "io_error"}:
            read_error += 1
    return {
        "depth_limit": depth,
        "file_limit_reached": file_limit,
        "read_error": read_error,
    }


def truncation_honesty_notes(coverage: dict[str, Any] | None) -> list[str]:
    """Human notes for report honesty panels and gate messages."""
    if not isinstance(coverage, dict):
        return []
    notes: list[str] = []
    events = coverage.get("parser_events") or []
    trunc = count_truncation_events(events if isinstance(events, list) else [])
    depth = int(coverage.get("depth_limit_count") or trunc["depth_limit"])
    file_limit = int(coverage.get("file_limit_reached_count") or trunc["file_limit_reached"])
    read_errors = int(coverage.get("read_error_count") or trunc["read_error"])
    if file_limit:
        notes.append(
            f"File walk truncated: file limit reached ({file_limit} event(s)). "
            "Authority beyond the cap was not inventoried."
        )
    if depth:
        notes.append(
            f"Directory depth limit hit ({depth} event(s)). "
            "Nested agent configs may be missing from this report."
        )
    if read_errors:
        notes.append(f"Read errors while scanning ({read_errors}).")
    unparsed = int(coverage.get("unparsed_agent_config_count") or 0)
    if unparsed:
        notes.append(f"NOT PARSED: {unparsed} agent config file(s) could not be read.")
    return notes


def family_coverage_line_from_coverage(
    coverage: dict[str, Any] | None,
    *,
    unparsed: int | None = None,
) -> str:
    """Honest maturity counts — never present supported_ratio as a clearance %."""
    if not isinstance(coverage, dict):
        return "Coverage: (unavailable)"
    by = coverage.get("component_counts_by_maturity") or {}
    supported = int(by.get("SUPPORTED") or 0)
    partial = int(by.get("PARTIAL") or 0)
    manual = int(by.get("MANUAL_ONLY") or 0)
    unsupported = int(by.get("UNSUPPORTED") or 0)
    if unparsed is None:
        unparsed = int(coverage.get("unparsed_agent_config_count") or 0)
    return (
        f"Coverage: SUPPORTED {supported} · PARTIAL {partial} · "
        f"MANUAL_ONLY {manual} · UNSUPPORTED {unsupported}"
        + (f" · NOT PARSED {unparsed}" if unparsed else "")
    )


def summarize_coverage(
    components: list[dict[str, Any]],
    *,
    parser_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    by_maturity: dict[str, int] = {
        "SUPPORTED": 0,
        "PARTIAL": 0,
        "MANUAL_ONLY": 0,
        "UNSUPPORTED": 0,
    }
    by_type: dict[str, int] = {}
    for comp in components:
        maturity = str(comp.get("adapter_maturity") or "PARTIAL").upper()
        if maturity not in by_maturity:
            by_maturity[maturity] = 0
        by_maturity[maturity] += 1
        ctype = str(comp.get("type") or "Unknown")
        by_type[ctype] = by_type.get(ctype, 0) + 1

    high_priority: list[dict[str, Any]] = []
    for comp in components:
        hints = comp.get("priority_hints") or []
        if hints:
            high_priority.append(
                {
                    "component_id": comp.get("component_id"),
                    "name": comp.get("name"),
                    "type": comp.get("type"),
                    "repository_path": comp.get("repository_path"),
                    "hints": hints,
                }
            )

    unparsed = count_unparsed_agent_configs(parser_events)
    trunc = count_truncation_events(parser_events)
    supported = by_maturity.get("SUPPORTED", 0)
    partial = by_maturity.get("PARTIAL", 0)
    total = max(len(components), 1)
    return {
        "adapter_matrix": ADAPTER_COVERAGE,
        "authority_layers": AUTHORITY_LAYERS,
        "component_counts_by_type": by_type,
        "component_counts_by_maturity": by_maturity,
        "deterministically_discovered": supported + partial,
        "supported_ratio": round(supported / total, 4),
        "unparsed_agent_config_count": unparsed,
        "depth_limit_count": trunc["depth_limit"],
        "file_limit_reached_count": trunc["file_limit_reached"],
        "read_error_count": trunc["read_error"],
        "truncated": bool(trunc["depth_limit"] or trunc["file_limit_reached"]),
        "parser_events": list(parser_events or [])[:50],
        "manual_review_families": [
            row["family"]
            for row in ADAPTER_COVERAGE
            if row["maturity"] in {"MANUAL_ONLY", "UNSUPPORTED"}
        ],
        "high_priority_review_areas": high_priority[:25],
        "not_verified": [
            "Runtime behavior",
            "Publisher identity",
            "Effective host permissions",
            "Credential isolation",
        ],
        "layer_honesty": (
            "Passive scans establish DECLARED/CONFIGURED authority only. "
            "EFFECTIVE and VERIFIED require host or authorized runtime evidence."
        ),
    }
