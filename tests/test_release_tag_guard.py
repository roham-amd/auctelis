"""AUCT-004 — release workflow refuses tag/version mismatch (dry-run)."""

from __future__ import annotations

from pathlib import Path


def _tag_matches_version(tag: str, version: str) -> bool:
    """Mirror the release.yml guard: GITHUB_REF_NAME must equal v$(VERSION)."""
    expected = f"v{version.strip()}"
    return tag == expected


def test_tag_guard_accepts_matching_tag():
    assert _tag_matches_version("v0.13.0", "0.13.0")


def test_tag_guard_rejects_mismatch():
    assert not _tag_matches_version("v0.12.2", "0.13.0")


def test_release_yml_contains_tag_guard():
    text = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")
    assert "Verify tag matches VERSION" in text
    assert "GITHUB_REF_NAME" in text
    assert 'expected="v$(tr -d' in text or 'expected="v$(tr -d' in text
