"""Authority file digests must be stable across CRLF/LF working trees."""

from __future__ import annotations

from pathlib import Path

from auctelis.supply_chain.digest import sha256_file


def test_sha256_file_text_newlines_normalizes_crlf(tmp_path: Path):
    lf = tmp_path / "lf.yml"
    crlf = tmp_path / "crlf.yml"
    lf.write_bytes(b"name: auctelis\nlocked: false\n")
    crlf.write_bytes(b"name: auctelis\r\nlocked: false\r\n")
    assert sha256_file(lf) != sha256_file(crlf)
    assert sha256_file(lf, text_newlines=True) == sha256_file(crlf, text_newlines=True)
