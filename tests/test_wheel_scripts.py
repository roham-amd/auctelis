"""AUCT-004 — product wheel exposes only the ``auctelis`` console script."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest


def test_built_wheel_exposes_only_auctelis_script(tmp_path: Path):
    """Build the product wheel and assert no ``auctelis-dev`` entry point."""
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    tools = root / "tools"
    dist = tmp_path / "dist"
    dist.mkdir()
    # Keep uv's cache/tool state inside tmp_path: the default per-user cache can
    # be locked or denied in sandboxes, silently skipping this release contract.
    env = {
        **os.environ,
        "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        "UV_TOOL_DIR": str(tmp_path / "uv-tools"),
        "UV_PYTHON_INSTALL_DIR": str(tmp_path / "uv-python"),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=tools,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        # Fallback: uv build when python -m build is unavailable.
        proc = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist)],
            cwd=tools,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    if proc.returncode != 0:
        pytest.skip(f"wheel build unavailable: {proc.stderr or proc.stdout}")
    wheels = list(dist.glob("auctelis-*.whl"))
    assert len(wheels) == 1, wheels
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
        entry_names = [n for n in names if n.endswith("entry_points.txt")]
        assert entry_names, "missing entry_points.txt in wheel"
        text = zf.read(entry_names[0]).decode("utf-8")
    assert "auctelis =" in text or "auctelis=" in text
    assert "auctelis-dev" not in text
    # Research / maintainer packages must not ship.
    assert not any(n.startswith("auctelis_research/") for n in names)
    assert not any(n.startswith("auctelis_devtools/") for n in names)
    for banned in (
        "auctelis/security/report.py",
        "auctelis/security/baseline.py",
        "auctelis/process_env.py",
        "auctelis/pins.py",
    ):
        assert banned not in names


def test_product_pyproject_has_no_dev_script():
    text = (Path(__file__).resolve().parents[1] / "tools" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert 'auctelis = "auctelis.cli:main"' in text
    assert "auctelis-dev =" not in text.split("[project.scripts]", 1)[1].split("[", 1)[0]
    assert (Path(__file__).resolve().parents[1] / "tools" / "dev" / "pyproject.toml").is_file()
