from pathlib import Path

from authdiff.pilots.runner import load_manifest, run_pilots


def test_pilot_manifest_lists_enabled_targets():
    manifest = load_manifest()
    ids = {p["id"] for p in manifest["pilots"] if p.get("enabled", True)}
    assert "skill-to-mcp-path" in ids
    assert "benign-skill-only" in ids


def test_pilots_run_subset(tmp_path: Path):
    report = run_pilots(
        output_dir=tmp_path / "results",
        only=["benign-skill-only", "skill-to-mcp-path"],
    )
    assert report["pilot_count"] == 2
    assert report["ok_count"] == 2
    assert Path(report["summary_md"]).is_file()
    by_id = {r["id"]: r for r in report["results"]}
    assert by_id["skill-to-mcp-path"]["finding_count"] >= 1
    assert by_id["benign-skill-only"]["finding_count"] == 0
