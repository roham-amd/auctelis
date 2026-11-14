"""Shared CLI guards for human-only mutations."""

from __future__ import annotations

import os


def refuse_agent_mutation(command: str) -> int | None:
    """Agents explain evidence; they must not mutate lock/policy/CODEOWNERS."""
    if os.environ.get("AUCTELIS_AGENT", "").strip() in {"1", "true", "yes"}:
        print(
            f"refused: `{command}` mutates authority state. "
            "Unset AUCTELIS_AGENT and have a human run watch --seal / lock / ci init."
        )
        return 2
    return None
