"""Unified authdiff audit orchestrator — profiles over passive discovery + agent handoff."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from authdiff.inventory.collector import collect_inventory, inventory_to_json
from authdiff.jsonio import write_json, write_text
from authdiff.paths import resolve_default_output_dir
from authdiff.preflight import (
    build_audit_context_md,
    inventory_to_graph,
    render_preflight_text,
    resolve_git_commit,
)
from authdiff.versioning import product_version

ProfileName = Literal["quick", "standard", "deployment"]


@dataclass(frozen=True, slots=True)
class ProfileSpec:
    name: ProfileName
    label: str
    purpose: str
    deliverable: str
    stages_expected: tuple[str, ...]
    deep_review: bool
    deployment_worksheet: bool

    def as_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("name", None)
        return data


PROFILES: dict[ProfileName, ProfileSpec] = {
    "quick": ProfileSpec(
        name="quick",
        label="Quick",
        purpose="Understand the agent ecosystem and surface obvious review priorities.",
        deliverable="Inventory and prioritized observations",
        stages_expected=("0-scope", "1-discovery", "2-candidates"),
        deep_review=False,
        deployment_worksheet=False,
    ),
    "standard": ProfileSpec(
        name="standard",
        label="Standard",
        purpose="Assess priority components and cross-component relationships with evidence.",
        deliverable="Evidence-backed security report (agent + human)",
        stages_expected=(
            "0-scope",
            "1-discovery",
            "2-candidates",
            "3-component-deep",
            "4-artifact",
            "5-host-integration",
            "6-cross-component",
        ),
        deep_review=True,
        deployment_worksheet=False,
    ),
    "deployment": ProfileSpec(
        name="deployment",
        label="Deployment",
        purpose="Evaluate a specific host, identity, data sensitivity, and runtime context.",
        deliverable="Deployment suitability assessment with explicit evidence gaps",
        stages_expected=(
            "0-scope",
            "1-discovery",
            "2-candidates",
            "3-component-deep",
            "4-artifact",
            "5-host-integration",
            "6-cross-component",
            "7-runtime-if-authorized",
            "8-production-suitability",
        ),
        deep_review=True,
        deployment_worksheet=True,
    ),
}

_MODULE_BY_TYPE: dict[str, str] = {
    "Skill": "archive/methodology/modules/skills.md",
    "MCP Server": "archive/methodology/modules/mcp.md",
    "MCP Client": "archive/methodology/modules/mcp.md",
    "MCP Server Registration": "archive/methodology/modules/mcp.md",
    "MCP Server Implementation": "archive/methodology/modules/mcp.md",
    "MCP": "archive/methodology/modules/mcp.md",
    "Plugin": "archive/methodology/modules/plugins.md",
    "Hook": "archive/methodology/modules/hooks.md",
    "Subagent": "archive/methodology/modules/subagents.md",
    "Automation": "archive/methodology/modules/automations.md",
    "A2A": "archive/methodology/modules/a2a.md",
    "Workflow": "archive/methodology/modules/automations.md",
    "CI Workflow": "archive/methodology/modules/automations.md",
    "Rule pack": "archive/methodology/modules/skills.md",
}


def suggest_modules(components: list[dict[str, Any]]) -> list[str]:
    suggested: list[str] = []
    seen: set[str] = set()
    for comp in components:
        ctype = str(comp.get("type") or "")
        module = _MODULE_BY_TYPE.get(ctype)
        if module is None:
            lowered = ctype.lower()
            for key, mod in _MODULE_BY_TYPE.items():
                if key.lower() in lowered:
                    module = mod
                    break
        if module and module not in seen:
            seen.add(module)
            suggested.append(module)
    if (
        any("multimodal" in str(c.get("priority_hints")).lower() for c in components)
        and "archive/methodology/modules/multimodal.md" not in seen
    ):
        suggested.append("archive/methodology/modules/multimodal.md")
    return suggested


def _stage_checklist(spec: ProfileSpec) -> str:
    lines = ["## Stage checklist (profile expectations)", ""]
    for stage in spec.stages_expected:
        lines.append(f"- [ ] `{stage}`")
    if not spec.deep_review:
        lines.extend(
            [
                "",
                "Deep component audit is **optional** for Quick. Escalate to "
                "`authdiff audit . --profile standard` when authority-bearing surfaces need review.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def deployment_worksheet() -> str:
    return """# Deployment suitability worksheet

Fill only with independently supported evidence. Missing cells → `NOT VERIFIED`, not pass.

| Question | Evidence class | Status | Notes |
| --- | --- | --- | --- |
| Exact host agent + version | HOST_CONFIGURATION | NOT VERIFIED | |
| Execution identity / service principal | HOST_CONFIGURATION | NOT VERIFIED | |
| Effective filesystem / network permissions | HOST_CONFIGURATION / RUNTIME | NOT VERIFIED | |
| Secrets / credential injection paths | HOST_CONFIGURATION | NOT VERIFIED | |
| Data sensitivity classification | USER_ASSERTION + policy | NOT VERIFIED | |
| Approval / human-in-the-loop gates | HOST_CONFIGURATION | NOT VERIFIED | |
| Artifact digests match reviewed sources | ARTIFACT / PROVENANCE | NOT VERIFIED | |
| Compensating controls outside the model | HOST_CONFIGURATION | NOT VERIFIED | |

## Production suitability gate

- [ ] Component trust reviewed for in-scope components
- [ ] Integration trust reviewed for this host binding
- [ ] Residual risks accepted by named owner
- [ ] Reassessment trigger defined (diff / baseline)

Do **not** treat inventory completeness as production approval.
"""


def enrich_audit_context(
    base_md: str,
    *,
    profile: ProfileName,
    components: list[dict[str, Any]],
) -> str:
    spec = PROFILES[profile]
    modules = suggest_modules(components)
    extra = [
        "",
        f"## Audit profile: {spec.label}",
        "",
        f"- Purpose: {spec.purpose}",
        f"- Expected deliverable: {spec.deliverable}",
        "",
        _stage_checklist(spec),
        "## Suggested modules (load only these)",
        "",
    ]
    if modules:
        extra.extend(f"- `{mod}`" for mod in modules)
    else:
        extra.append("- None selected from inventory types; use discovery to choose modules.")
    extra.extend(
        [
            "",
            "## Finding discipline",
            "",
            "- Separate OBSERVED / CONFIRMED / POTENTIAL / NOT VERIFIED.",
            "- Trace attacker control → entry → trust boundary → privileged capability → control → effect.",
            "- Validate JSON with `authdiff validate report` before claiming success.",
            "",
        ]
    )
    return base_md.rstrip() + "\n" + "\n".join(extra)


def render_audit_summary(
    *,
    profile: ProfileName,
    summary_text: str,
    out_dir: Path,
) -> str:
    spec = PROFILES[profile]
    body = summary_text.replace(
        "authdiff — Agent Ecosystem Preflight",
        f"authdiff — Agent Ecosystem Assessment ({spec.label})",
    ).replace(
        "authdiff Gate — Agent Ecosystem Preflight",
        f"authdiff — Agent Ecosystem Assessment ({spec.label})",
    )
    if body.startswith("authdiff —"):
        return body
    header = [
        f"authdiff — Agent Ecosystem Assessment ({spec.label} profile)",
        f"Purpose: {spec.purpose}",
        "",
    ]
    return "\n".join(header) + body + f"\n  Profile metadata: {out_dir.as_posix()}/profile.json\n"


def run_audit(
    target: Path,
    *,
    profile: ProfileName = "standard",
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    spec = PROFILES[profile]

    target = target.resolve()
    out_dir = (output_dir or resolve_default_output_dir()).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    result = collect_inventory(target)
    commit = resolve_git_commit(target)
    inventory = inventory_to_json(result)
    if commit:
        inventory["repository_commit"] = commit

    modules = suggest_modules(result.components)
    context_md = enrich_audit_context(
        build_audit_context_md(result, commit=commit),
        profile=profile,
        components=result.components,
    )
    summary_text = render_audit_summary(
        profile=profile,
        summary_text=render_preflight_text(result, commit=commit, out_dir=out_dir),
        out_dir=out_dir,
    )

    profile_doc = {
        "authdiff_audit_profile": profile,
        "product": "authdiff",
        "product_version": product_version(),
        "product_version_hint": product_version(),
        **spec.as_public_dict(),
        "suggested_modules": modules,
        "limitations": [
            "Deterministic phase emits inventory and optional Guard rule findings via `authdiff scan`.",
            "Deep semantic review requires an AI agent or human following the procedure.",
            "Inventory coverage is partial; see inventory.json coverage.adapter_matrix.",
        ],
    }

    write_json(out_dir / "inventory.json", inventory)
    write_json(
        out_dir / "ecosystem-graph.json",
        inventory_to_graph(result, commit=commit, audit_id=f"audit-{profile}"),
    )
    write_text(out_dir / "audit-context.md", context_md)
    write_text(out_dir / "audit-summary.md", summary_text)
    write_text(out_dir / "preflight-summary.md", summary_text)
    write_json(out_dir / "profile.json", profile_doc)

    if spec.deployment_worksheet:
        write_text(out_dir / "deployment-worksheet.md", deployment_worksheet())

    return {
        "output_dir": str(out_dir),
        "profile": profile,
        "commit": commit,
        "component_count": len(result.components),
        "coverage": result.coverage,
        "summary": summary_text,
        "suggested_modules": modules,
    }
