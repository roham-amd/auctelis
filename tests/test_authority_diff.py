"""Golden-ish tests for Authority Snapshot, new-only gating, and pin semantics."""

from __future__ import annotations

from pathlib import Path

from authdiff.inventory.adapters.mcp import _package_looks_pinned
from authdiff.security.authority import build_authority_snapshot, diff_authority_snapshots
from authdiff.security.baseline import diff_against_baseline, save_baseline
from authdiff.security.decision import compute_decision
from authdiff.security.scan import run_scan
from authdiff.vet import resolve_vet_source


def test_package_pin_semantics():
    assert _package_looks_pinned("pkg@1.2.3")
    assert _package_looks_pinned("@scope/pkg@1.2.3")
    assert not _package_looks_pinned("pkg@latest")
    assert not _package_looks_pinned("@scope/pkg@next")
    assert not _package_looks_pinned("@scope/pkg")
    assert not _package_looks_pinned("git@github.com:org/repo.git")
    assert _package_looks_pinned("pkg@sha256:deadbeef")


def test_open_parser_readme_example():
    _, url = resolve_vet_source("github.com/org/some-skill")
    assert url == "https://github.com/org/some-skill.git"


def test_authority_snapshot_and_new_only_decision(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text(
        '{"mcpServers":{"demo":{"command":"npx","args":["-y","demo-pkg"]}}}',
        encoding="utf-8",
    )
    out1 = tmp_path / "out1"
    scan1, _, _ = run_scan(root, output_dir=out1, fail_on=None)
    snap1 = build_authority_snapshot(scan1)
    assert snap1["snapshot_hash"]
    assert (out1 / "authority-snapshot.json").is_file()

    base_path = tmp_path / "baseline.json"
    save_baseline(scan1, base_path)

    # Identical head → zero delta → NO-GATED-FINDINGS even if findings exist.
    out2 = tmp_path / "out2"
    scan2, payload, code = run_scan(root, output_dir=out2, baseline=base_path, fail_on="high")
    assert code == 0
    assert payload["risk_delta"]["high_or_critical_findings_added"] == 0
    decision = compute_decision(
        scan2.findings,
        coverage=scan2.coverage,
        risk_delta=payload["risk_delta"],
    )
    assert decision == "NO-GATED-FINDINGS"

    delta = diff_against_baseline(scan2, {"finding_keys": [], "component_fingerprints": []})
    assert "gated_new_findings" in delta["changes"]


def test_authority_component_delta_detects_add(tmp_path: Path):
    base = {
        "snapshot_hash": "aaa",
        "components": [
            {
                "fingerprint": "fp1",
                "path": ".cursor/mcp.json",
                "kind": "MCP Server Registration",
                "capabilities": [],
                "approval_posture": "prompt",
                "pin_state": "pinned",
            }
        ],
    }
    head = {
        "snapshot_hash": "bbb",
        "components": [
            {
                "fingerprint": "fp2",
                "path": ".cursor/mcp.json",
                "kind": "MCP Server Registration",
                "capabilities": ["execute"],
                "approval_posture": "auto",
                "pin_state": "floating",
                "destinations": [],
                "identity": [],
            }
        ],
    }
    delta = diff_authority_snapshots(base, head)
    assert delta["summary"]["components_modified"] >= 1 or delta["summary"]["components_added"] >= 1
