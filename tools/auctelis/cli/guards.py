"""Shared CLI guards for human-only mutations and research boundary."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def refuse_agent_mutation(command: str) -> int | None:
    """Agents explain evidence; they must not mutate lock/policy/CODEOWNERS."""
    if os.environ.get("AUCTELIS_AGENT", "").strip() in {"1", "true", "yes"}:
        print(
            f"refused: `{command}` mutates authority state. "
            "Unset AUCTELIS_AGENT and have a human run lock / init."
        )
        return 2
    return None


def require_research() -> None:
    """Research scanner lives outside the product wheel (source / editable only)."""
    try:
        import auctelis_research as _research

        _ = _research
        return
    except ImportError:
        pass
    import auctelis as _pkg

    tools_dir = Path(_pkg.__file__).resolve().parents[1]
    tools_s = str(tools_dir)
    if tools_s not in sys.path:
        sys.path.insert(0, tools_s)
    try:
        import auctelis_research as _research

        _ = _research
    except ImportError as exc:
        raise SystemExit(
            "Research helpers require a source checkout "
            "(auctelis_research is not shipped in the product wheel)."
        ) from exc
