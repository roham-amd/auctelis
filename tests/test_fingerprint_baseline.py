"""Rename-resilience and baseline identity integration tests."""

from __future__ import annotations

import shutil
from pathlib import Path

from auctelis.security.baseline import diff_against_baseline, save_baseline
from auctelis.security.engine import run_security_scan
from auctelis.security.fingerprint import (
    component_fingerprint,
    finding_key,
    paths_by_fingerprint,
)


def _write_skill(root: Path, folder: str, body: str, *, name: str | None = None) -> Path:
    skill_dir = root / "skills" / folder
    skill_dir.mkdir(parents=True, exist_ok=True)
    front = f"---\nname: {name or folder}\ndescription: fixture\n---\n\n"
    (skill_dir / "SKILL.md").write_text(front + body, encoding="utf-8")
    return skill_dir


def _write_mcp(root: Path, path: str, command: str = "npx") -> Path:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '{\n  "mcpServers": {\n    "local-echo": {\n'
        f'      "command": "{command}",\n'
        '      "args": ["-y", "@modelcontextprotocol/server-everything"]\n'
        "    }\n  }\n}\n",
        encoding="utf-8",
    )
    return target


def test_fingerprint_stable_across_skill_rename(tmp_path: Path):
    root = tmp_path / "repo"
    _write_skill(root, "helper-a", "Read the open file.\n", name="helper")
    scan1 = run_security_scan(root)
    skills = [c for c in scan1.inventory["components"] if c["type"] == "Skill"]
    assert len(skills) == 1
    fp1 = skills[0]["fingerprint"]

    # Rename folder; keep frontmatter name + body identical.
    shutil.move(str(root / "skills" / "helper-a"), str(root / "skills" / "helper-b"))
    scan2 = run_security_scan(root)
    skills2 = [c for c in scan2.inventory["components"] if c["type"] == "Skill"]
    assert len(skills2) == 1
    assert skills2[0]["fingerprint"] == fp1
    assert skills2[0]["repository_path"] != skills[0]["repository_path"]


def test_fingerprint_stable_across_mcp_move(tmp_path: Path):
    root = tmp_path / "repo"
    _write_mcp(root, ".cursor/mcp.json")
    scan1 = run_security_scan(root)
    mcp = [c for c in scan1.inventory["components"] if c["type"] == "MCP Server Registration"]
    assert mcp
    fp1 = mcp[0]["fingerprint"]

    # Move within the same host tree — host_id stays `cursor`, record digest unchanged.
    src = root / ".cursor" / "mcp.json"
    dst = root / ".cursor" / "nested" / "mcp.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    scan2 = run_security_scan(root)
    mcp2 = [c for c in scan2.inventory["components"] if c["type"] == "MCP Server Registration"]
    assert mcp2
    assert mcp2[0]["fingerprint"] == fp1


def test_mcp_copy_to_other_host_is_new_fingerprint(tmp_path: Path):
    root = tmp_path / "repo"
    _write_mcp(root, ".cursor/mcp.json")
    scan1 = run_security_scan(root)
    fp_cursor = next(
        c["fingerprint"]
        for c in scan1.inventory["components"]
        if c["type"] == "MCP Server Registration"
    )
    body = (root / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    claude = root / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    (claude / "mcp.json").write_text(body, encoding="utf-8")
    scan2 = run_security_scan(root)
    fps = {
        (c.get("host_id"), c["fingerprint"])
        for c in scan2.inventory["components"]
        if c["type"] == "MCP Server Registration"
    }
    assert ("cursor", fp_cursor) in fps
    assert any(host == "claude-code" and fp != fp_cursor for host, fp in fps)


def test_content_change_changes_fingerprint(tmp_path: Path):
    root = tmp_path / "repo"
    _write_skill(root, "helper", "Version one.\n", name="helper")
    scan1 = run_security_scan(root)
    fp1 = next(c["fingerprint"] for c in scan1.inventory["components"] if c["type"] == "Skill")
    _write_skill(root, "helper", "Version two — different bytes.\n", name="helper")
    scan2 = run_security_scan(root)
    fp2 = next(c["fingerprint"] for c in scan2.inventory["components"] if c["type"] == "Skill")
    assert fp1 != fp2


def test_duplicate_names_distinct_content_distinct_fingerprints(tmp_path: Path):
    root = tmp_path / "repo"
    _write_skill(root, "alpha", "Body A\n", name="shared-name")
    _write_skill(root, "beta", "Body B different\n", name="shared-name")
    scan = run_security_scan(root)
    skills = [c for c in scan.inventory["components"] if c["type"] == "Skill"]
    assert len(skills) == 2
    fps = {c["fingerprint"] for c in skills}
    assert len(fps) == 2


def test_identical_file_bytes_share_fingerprint(tmp_path: Path):
    root = tmp_path / "repo"
    body = "Identical body for clone test.\n"
    # Same frontmatter + body ⇒ identical file bytes at two paths.
    _write_skill(root, "one", body, name="clone")
    _write_skill(root, "two", body, name="clone")
    scan = run_security_scan(root)
    skills = [c for c in scan.inventory["components"] if c["type"] == "Skill"]
    fps = {c["fingerprint"] for c in skills}
    assert len(fps) == 1
    mapping = paths_by_fingerprint(skills)
    assert len(next(iter(mapping.values()))) == 2


def test_baseline_rename_is_move_not_add_remove(tmp_path: Path):
    root = tmp_path / "repo"
    _write_skill(root, "helper-a", "Stable skill body.\n", name="helper")
    _write_mcp(root, ".cursor/mcp.json")
    scan1 = run_security_scan(root)
    baseline = save_baseline(scan1, tmp_path / "baseline.json")
    assert baseline["baseline_version"] == "1.3"

    shutil.move(str(root / "skills" / "helper-a"), str(root / "skills" / "helper-renamed"))
    scan2 = run_security_scan(root)
    delta = diff_against_baseline(scan2, baseline)

    assert delta["summary"]["fingerprints_added"] == 0
    assert delta["summary"]["fingerprints_removed"] == 0
    assert delta["summary"]["components_moved"] >= 1
    assert delta["summary"]["findings_added"] == 0
    assert delta["policy_hints"]["rename_or_move_only"] is True
    assert delta["policy_hints"]["block_if_high_or_critical_added"] is False


def test_baseline_detects_genuine_new_component(tmp_path: Path):
    root = tmp_path / "repo"
    _write_skill(root, "helper", "Only skill.\n", name="helper")
    scan1 = run_security_scan(root)
    baseline = save_baseline(scan1, tmp_path / "baseline.json")

    _write_mcp(
        root,
        ".cursor/mcp.json",
        command="npx",
    )
    # Broad args → new security finding identity.
    (root / ".cursor" / "mcp.json").write_text(
        '{\n  "mcpServers": {\n    "filesystem-broad": {\n'
        '      "command": "npx",\n'
        '      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/"]\n'
        "    }\n  }\n}\n",
        encoding="utf-8",
    )
    scan2 = run_security_scan(root)
    delta = diff_against_baseline(scan2, baseline)
    assert delta["summary"]["fingerprints_added"] >= 1
    assert delta["summary"]["high_or_critical_findings_added"] >= 1
    assert delta["policy_hints"]["block_if_high_or_critical_added"] is True


def test_baseline_content_change_is_modification_not_unrelated_churn(tmp_path: Path):
    root = tmp_path / "repo"
    _write_skill(root, "helper", "Version one.\n", name="helper")
    scan1 = run_security_scan(root)
    baseline = save_baseline(scan1, tmp_path / "baseline.json")
    path = next(c["repository_path"] for c in scan1.inventory["components"] if c["type"] == "Skill")

    _write_skill(root, "helper", "Version two — different bytes.\n", name="helper")
    scan2 = run_security_scan(root)
    delta = diff_against_baseline(scan2, baseline)

    assert delta["summary"]["components_modified"] == 1
    assert delta["changes"]["components_modified"][0]["path"] == path
    assert delta["changes"]["components_modified"][0]["kind"] == "content_modification"
    # Same-path edits must not look like unrelated fingerprint add+remove.
    assert delta["summary"]["fingerprints_added"] == 0
    assert delta["summary"]["fingerprints_removed"] == 0
    assert delta["policy_hints"]["content_modification_only"] is True


def test_baseline_clone_preserves_fingerprint_identity(tmp_path: Path):
    root = tmp_path / "repo"
    body = "Clone-stable body.\n"
    _write_skill(root, "original", body, name="clone")
    scan1 = run_security_scan(root)
    baseline = save_baseline(scan1, tmp_path / "baseline.json")
    fp = next(c["fingerprint"] for c in scan1.inventory["components"] if c["type"] == "Skill")

    _write_skill(root, "copy", body, name="clone")
    scan2 = run_security_scan(root)
    delta = diff_against_baseline(scan2, baseline)
    skills = [c for c in scan2.inventory["components"] if c["type"] == "Skill"]
    assert {c["fingerprint"] for c in skills} == {fp}
    assert delta["summary"]["fingerprints_added"] == 0
    assert delta["summary"]["fingerprints_removed"] == 0
    assert delta["summary"]["components_modified"] == 0
    assert delta["summary"]["components_moved"] >= 1


def test_finding_key_ignores_component_id_reshuffle():
    assert finding_key(
        "AUCTELIS-RULE-002", fingerprint="abcd1234abcd1234", component_ids=["C-001"]
    ) == (finding_key("AUCTELIS-RULE-002", fingerprint="abcd1234abcd1234", component_ids=["C-099"]))


def test_digest_backed_fingerprint_ignores_path():
    a = {
        "type": "Skill",
        "adapter": "skill_md",
        "content_digest": "sha256:abc",
        "name": "x",
        "repository_path": "skills/a/SKILL.md",
    }
    b = {
        "type": "Skill",
        "adapter": "skill_md",
        "content_digest": "sha256:abc",
        "name": "y",
        "repository_path": "skills/moved/SKILL.md",
    }
    assert component_fingerprint(a) == component_fingerprint(b)
