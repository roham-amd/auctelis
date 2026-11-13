"""Registry of deterministic discovery adapters (extensibility point)."""

from __future__ import annotations

from auctelis.inventory.adapters.claude_settings import discover_claude_settings
from auctelis.inventory.adapters.hooks import discover_hooks
from auctelis.inventory.adapters.host_components import (
    discover_automations,
    discover_plugins,
    discover_subagents,
)
from auctelis.inventory.adapters.hosts import discover_host_profiles
from auctelis.inventory.adapters.mcp import discover_mcp_configs
from auctelis.inventory.adapters.rules_a2a import discover_agent_cards, discover_instruction_rules
from auctelis.inventory.adapters.skills import discover_skills
from auctelis.inventory.adapters.toml_config import discover_toml_mcp_configs
from auctelis.inventory.adapters.workflows import discover_github_workflows
from auctelis.inventory.types import DiscoveryAdapter

# Order is stable for component_id assignment across runs on the same tree.
DISCOVERY_ADAPTERS: tuple[DiscoveryAdapter, ...] = (
    discover_skills,
    discover_mcp_configs,
    discover_toml_mcp_configs,
    discover_claude_settings,
    discover_agent_cards,
    discover_instruction_rules,
    discover_hooks,
    discover_plugins,
    discover_subagents,
    discover_automations,
    discover_github_workflows,
    discover_host_profiles,
)
