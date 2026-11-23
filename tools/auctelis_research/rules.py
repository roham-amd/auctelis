"""Re-exports deterministic rules from the product security package."""

from __future__ import annotations

from auctelis.security.rules import (
    CROSS_COMPONENT_RULE_IDS,
    RULES,
    RuleSpec,
    apply_all_rules,
)

__all__ = [
    "CROSS_COMPONENT_RULE_IDS",
    "RULES",
    "RuleSpec",
    "apply_all_rules",
]
