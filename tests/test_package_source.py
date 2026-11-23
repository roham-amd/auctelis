"""AUCT-063: non-executing package archive extraction and MCP server hints."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

from auctelis.inventory.adapters.mcp import discover_mcp_configs
from auctelis.inventory.limits import CollectorLimits
from auctelis.security.package_source import (
    extract_archive_text_files,
    fetch_package_archive,
)


def _tar_gz(members: list[tuple[str, bytes | None, str, str | None]]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data, kind, linkname in members:
            info = tarfile.TarInfo(name=name)
            if kind == "reg":
                assert data is not None
                info.type = tarfile.REGTYPE
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            elif kind == "sym":
                info.type = tarfile.SYMTYPE
                info.linkname = linkname or "/etc/passwd"
                tf.addfile(info)
            elif kind == "lnk":
                info.type = tarfile.LNKTYPE
                info.linkname = linkname or "package/ok.py"
                tf.addfile(info)
    return buf.getvalue()


def test_extract_tar_rejects_traversal_and_symlinks() -> None:
    archive = _tar_gz(
        [
            ("package/ok.py", b"print('safe')\n", "reg", None),
            ("package/../escape.py", b"BAD\n", "reg", None),
            ("/abs.py", b"ABS\n", "reg", None),
            ("package/link.py", None, "sym", "/etc/passwd"),
            ("package/hard.py", None, "lnk", "package/ok.py"),
        ]
    )
    files = extract_archive_text_files(archive, kind="tar.gz")
    assert "ok.py" in files
    assert files["ok.py"] == "print('safe')\n"
    assert "escape.py" not in files
    assert "../escape.py" not in files
    assert "abs.py" not in files
    assert "/abs.py" not in files
    assert "link.py" not in files
    assert "hard.py" not in files


def test_fetch_pypi_prefers_wheel_over_sdist() -> None:
    called: list[str] = []

    def fetcher(url: str) -> bytes:
        called.append(url)
        return b"PK\x03\x04wheel-bytes"

    meta = {
        "urls": [
            {
                "packagetype": "sdist",
                "url": "https://files.pythonhosted.org/packages/a/pkg-1.0.tar.gz",
            },
            {
                "packagetype": "bdist_wheel",
                "url": "https://files.pythonhosted.org/packages/b/pkg-1.0-py3-none-any.whl",
            },
        ]
    }
    data, kind = fetch_package_archive("pypi", meta, fetcher=fetcher)
    assert kind == "zip"
    assert data == b"PK\x03\x04wheel-bytes"
    assert called == ["https://files.pythonhosted.org/packages/b/pkg-1.0-py3-none-any.whl"]


def test_mcp_source_emits_env_and_shell_hints(tmp_path: Path) -> None:
    src = tmp_path / "mcp_server.py"
    src.write_text(
        "import os\n"
        "import subprocess\n"
        "from mcp.server import Server\n"
        "x = os.environ.get('TOKEN')\n"
        "subprocess.run(['echo', 'hi'])\n",
        encoding="utf-8",
    )
    comps = discover_mcp_configs(tmp_path, files=[src], limits=CollectorLimits(), events=[])
    assert comps
    hints = comps[0].get("priority_hints") or []
    assert "env_access_in_server" in hints
    assert "shell_exec_in_server" in hints
