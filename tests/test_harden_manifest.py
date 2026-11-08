from pathlib import Path

from authdiff.authority_manifest import init_manifest, verify_manifest
from authdiff.harden import run_harden
from authdiff.security.scan import run_scan


def test_harden_rejects_apply(tmp_path: Path):
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"
    scan, payload, _code = run_scan(demo, output_dir=tmp_path / "out")
    assert scan.findings
    findings = Path(payload["output_dir"]) / "findings.json"
    text, code = run_harden(findings_path=findings, apply=True)
    assert code == 2
    assert "disabled" in text.lower()
    text_ok, code_ok = run_harden(findings_path=findings, apply=False)
    assert code_ok == 0
    assert "dry-run" in text_ok.lower()


def test_authority_manifest_roundtrip(tmp_path: Path):
    # Isolated root so inventory is deterministic for the round-trip.
    root = tmp_path / "repo"
    skill = root / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: demo\n---\nhello\n",
        encoding="utf-8",
    )
    msg, code = init_manifest(root)
    assert code == 0
    assert "Wrote draft" in msg
    assert (root / "AUTHORITY.yml").is_file()
    report, vcode = verify_manifest(root)
    assert vcode == 0
    assert report["ok"] is True
    assert report["verdict"] in {"MATCH", "DRIFT"}

    # Undeclared growth fails
    extra = root / "skills" / "extra"
    extra.mkdir()
    (extra / "SKILL.md").write_text("---\nname: extra\n---\nx\n", encoding="utf-8")
    report2, vcode2 = verify_manifest(root)
    assert vcode2 == 1
    assert report2["ok"] is False
    assert report2["undeclared_components"]


def test_scan_writes_pr_comment_once(tmp_path: Path):
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"
    _scan, payload, _code = run_scan(demo, output_dir=tmp_path / "out")
    comment_path = Path(payload["output_dir"]) / "pr-comment.md"
    assert comment_path.is_file()
    assert "Decision:" in comment_path.read_text(encoding="utf-8")
    assert payload.get("pr_comment")
