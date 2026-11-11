"""Week-4: short default report + Atlas precision gate."""

from __future__ import annotations

from pathlib import Path

from authdiff.cli import main
from authdiff.security.report import render_short_terminal_report, render_terminal_report
from authdiff.security.scan import run_scan


def _demo() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "demo-vulnerable"


def test_default_report_is_short(tmp_path: Path):
    _scan, payload, _code = run_scan(_demo(), output_dir=tmp_path / "out")
    short = payload["summary"]
    assert "DECISION:" in short
    assert len(short.splitlines()) <= 15
    assert "AUTHORITY SURFACES" not in short
    # Slim default artifacts — no full dump unless --full.
    assert not (tmp_path / "out" / "scan-summary-full.txt").is_file()
    assert (tmp_path / "out" / "pr-comment.md").is_file()
    assert (tmp_path / "out" / "findings.json").is_file()


def test_full_flag_lengthens_report(tmp_path: Path):
    scan, _p, _c = run_scan(_demo(), output_dir=tmp_path / "out", full_report=True)
    text = render_terminal_report(scan, full=True)
    assert len(text.splitlines()) > 30
    assert render_short_terminal_report(scan).count("\n") < text.count("\n")
    full_path = tmp_path / "out" / "scan-summary-full.txt"
    assert full_path.is_file()
    assert "AUTHORITY SURFACES" in full_path.read_text(encoding="utf-8")
    assert (tmp_path / "out" / "inventory.json").is_file()


def test_product_cli_hides_maintainer_commands():
    from authdiff.cli.parser import build_parser, normalize_argv

    product = build_parser(include_dev=False)
    assert "lock" in product.format_help()
    assert "demo" in product.format_help()
    # Advanced surface remains callable but is omitted from listed commands.
    args_adv = product.parse_args(["artifact-vet", "npm:left-pad"])
    assert args_adv.command == "artifact-vet"
    listed = "\n".join(
        line for line in product.format_help().splitlines() if line.startswith("    ")
    )
    assert "artifact-vet" not in listed
    # Bare argv normalizes to scan before parse.
    args_scan = product.parse_args(normalize_argv([]))
    assert args_scan.command == "scan"
    try:
        product.parse_args(["build", "all"])
        ok = True
    except SystemExit:
        ok = False
    assert ok is False
    dev = build_parser(include_dev=True)
    args = dev.parse_args(["build", "all"])
    assert args.command == "build"


def test_init_gate_writes_codeowners(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["ci", "init", str(root), "--owner", "@sec-owners"]) == 0
    assert (root / ".authdiff.yml").is_file()
    assert (root / ".github" / "workflows" / "authdiff-gate.yml").is_file()
    owners = (root / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "AUTHORITY.lock" in owners
    assert "@sec-owners" in owners
