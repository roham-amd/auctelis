"""Ensure ``auctelis_research`` (source-only) is importable during tests."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
_TOOLS_STR = str(_TOOLS)
if _TOOLS_STR not in sys.path:
    sys.path.insert(0, _TOOLS_STR)


def pytest_load_initial_conftests(early_config, parser, args: list[str]) -> None:
    """Force basetemp under the system temp dir before pytest creates it."""
    del early_config, parser  # unused; signature required by pytest hook
    if any(a == "--basetemp" or a.startswith("--basetemp=") for a in args):
        return
    base = (Path(tempfile.gettempdir()) / "auctelis-pytest").resolve()
    base.mkdir(parents=True, exist_ok=True)
    args.insert(0, f"--basetemp={base}")
