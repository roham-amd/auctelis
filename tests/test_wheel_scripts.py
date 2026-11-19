"""AUCT-004 — product wheel exposes only the ``auctelis`` console script."""

from __future__ import annotations

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
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=tools,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        # Fallback: uv build when python -m build is unavailable.
        proc = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist)],
            cwd=tools,
            capture_output=True,
            text=True,
            check=False,
        )
    if proc.returncode != 0:
        pytest.skip(f"wheel build unavailable: {proc.stderr or proc.stdout}")
    wheels = list(dist.glob("auctelis-*.whl"))
    assert len(wheels) == 1, wheels
    with zipfile.ZipFile(wheels[0]) as zf:
        entry_names = [n for n in zf.namelist() if n.endswith("entry_points.txt")]
        assert entry_names, "missing entry_points.txt in wheel"
        text = zf.read(entry_names[0]).decode("utf-8")
    assert "auctelis =" in text or "auctelis=" in text
    assert "auctelis-dev" not in text
    # Research package must not ship.
    assert not any(n.startswith("auctelis_research/") for n in zf.namelist())


def test_product_pyproject_has_no_dev_script():
    text = (Path(__file__).resolve().parents[1] / "tools" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert 'auctelis = "auctelis.cli:main"' in text
    assert "auctelis-dev =" not in text.split("[project.scripts]", 1)[1].split("[", 1)[0]
    assert (Path(__file__).resolve().parents[1] / "tools" / "dev" / "pyproject.toml").is_file()
