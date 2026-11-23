"""Week-4: short default report + Atlas precision gate."""

from __future__ import annotations

from pathlib import Path

from auctelis_devtools.cli import main_dev as main
from auctelis_research.report import (
    render_short_terminal_report,
    render_terminal_report,
)
from auctelis_research.scan import run_scan


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


def test_product_cli_hides_maintainer_commands(tmp_path: Path):
    from auctelis.cli.parser import CORE_PUBLIC_COMMANDS, build_parser, normalize_argv

    product = build_parser(include_dev=False)
    assert frozenset({"inspect", "diff"}) == CORE_PUBLIC_COMMANDS
    help_text = product.format_help()
    assert "inspect" in help_text
    assert "diff" in help_text
    listed = "\n".join(
        line
        for line in help_text.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
    )
    assert "inspect" in listed
    assert "diff" in listed
    assert not any(
        line.strip().startswith(name)
        for line in listed.splitlines()
        for name in ("lock", "demo", "check", "gate", "init")
    )
    assert "artifact-vet" not in listed
    # Advanced moved to auctelis-dev.
    try:
        product.parse_args(["artifact-vet", "npm:left-pad"])
        product_has_adv = True
    except SystemExit:
        product_has_adv = False
    assert product_has_adv is False
    # Bare argv → inspect (public front door).
    empty = tmp_path / "no-config"
    empty.mkdir()
    args_bare = product.parse_args(normalize_argv([], cwd=empty))
    assert args_bare.command == "inspect"
    try:
        product.parse_args(["build", "all"])
        ok = True
    except SystemExit:
        ok = False
    assert ok is False
    try:
        product.parse_args(["check", "."])
        product_has_check = True
    except SystemExit:
        product_has_check = False
    assert product_has_check is False
    dev = build_parser(include_dev=True)
    args = dev.parse_args(["build", "all"])
    assert args.command == "build"
    args_adv = dev.parse_args(["artifact-vet", "npm:left-pad"])
    assert args_adv.command == "artifact-vet"


def test_ci_init_writes_codeowners(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    assert main(["ci", "init", str(root), "--owner", "@sec-owners"]) == 0
    assert (root / ".auctelis.yml").is_file()
    assert (root / ".github" / "workflows" / "auctelis-gate.yml").is_file()
    owners = (root / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "AUTHORITY.lock" in owners
    assert "@sec-owners" in owners
