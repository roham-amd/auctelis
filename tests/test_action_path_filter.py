"""Regression tests for action.yml watched-path filter and shallow-clone safety."""

from __future__ import annotations

import re
from pathlib import Path

from auctelis.security.engine import run_authority_inventory

_ROOT = Path(__file__).resolve().parents[1]
_ACTION_PATH = _ROOT / ".github" / "actions" / "auctelis-gate" / "action.yml"


def _load_path_filter_regex(action_text: str) -> re.Pattern[str]:
    match = re.search(r"grep -iE '([^']+)'", action_text)
    assert match is not None, "action.yml path_filter grep -iE regex missing"
    return re.compile(match.group(1), re.IGNORECASE)


def test_path_filter_matches_all_authority_fixture_surfaces():
    text = _ACTION_PATH.read_text(encoding="utf-8")
    pattern = _load_path_filter_regex(text)

    # Every authority-bearing file discovered across eval/configs, attack-replay,
    # and atlas fixtures must match the Action's watched-path filter.
    discovered_paths: set[str] = set()
    for base in (
        _ROOT / "eval" / "configs",
        _ROOT / "examples" / "attack-replay",
        _ROOT / "tests" / "atlas" / "attacks",
        _ROOT / "tests" / "atlas" / "benign",
    ):
        for sample in sorted(base.iterdir()):
            if not sample.is_dir():
                continue
            scan = run_authority_inventory(sample, default_excludes=False)
            for comp in scan.inventory.get("components") or []:
                rel = str(comp.get("repository_path") or "").replace("\\", "/")
                if rel:
                    discovered_paths.add(rel)

    assert discovered_paths
    for rel in sorted(discovered_paths):
        assert pattern.search(rel), f"path_filter missed discovered authority path: {rel}"

    # Also verify synthetic surfaces across all adapters and protection files.
    synthetic_watched = [
        "hooks.json",
        "hooks/pre.py",
        "plugin.json",
        "my-plugin/package.json",
        "agents/helper.md",
        "subagents.json",
        "automations/nightly.yml",
        ".well-known/agent-card.json",
        ".cursorrules",
        ".windsurfrules",
        ".clinerules",
        "CODEX.md",
        ".github/copilot-instructions.md",
        ".codex/config.toml",
        ".cursor/mcp.json",
        ".claude/settings.json",
        "AUTHORITY.lock",
        ".auctelis.yml",
        ".auctelis/trusted-hosts",
        "CODEOWNERS",
        ".github/CODEOWNERS",
        ".github/workflows/ci.yml",
        ".github/actions/auctelis-gate/action.yml",
    ]
    for rel in synthetic_watched:
        assert pattern.search(rel), f"path_filter missed synthetic watched path: {rel}"

    # Unrelated files must bypass uv sync in lockless mode.
    unrelated = [
        "src/app.py",
        "README.md",
        ".cargo/config.toml",
        "package.json",
        "Cargo.toml",
        "docs/guide.md",
        "tests/test_app.py",
    ]
    for rel in unrelated:
        assert not pattern.search(rel), f"path_filter unexpectedly matched unrelated path: {rel}"


def test_action_uses_shallow_two_dot_diff_and_base_codeowners_for_policy():
    text = _ACTION_PATH.read_text(encoding="utf-8")
    assert 'git diff --name-only "${base}...HEAD"' not in text
    assert 'git diff --name-only "${base}..HEAD"' in text
    assert 'git show "${base}:${cand}"' in text
