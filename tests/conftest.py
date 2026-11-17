"""Ensure ``auctelis_research`` (source-only) is importable during tests."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
_TOOLS_STR = str(_TOOLS)
if _TOOLS_STR not in sys.path:
    sys.path.insert(0, _TOOLS_STR)
