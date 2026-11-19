"""Terminal / Markdown hygiene for untrusted repository-controlled text."""

from __future__ import annotations

import json
from pathlib import Path

from auctelis.check import build_check_report, render_check, why_repo
from auctelis.gate import render_gate_report
from auctelis.textutil import (
    escape_markdown,
    sanitize_terminal_line,
    sanitize_terminal_text,
    strip_control,
)

_ANSI = "\x1b[2J"
_OSC = "\x1b]0;spoofed title\x07"
_BIDI = "\u202e"
_ZWSP = "\u200b"
_BEL = "\x07"
_BS = "\x08"
_BOM = "\ufeff"


def test_strip_control_removes_terminal_and_bidi_formatting():
    raw = f"before{_ANSI}{_OSC}{_BEL}{_BS}{_BIDI}middle{_ZWSP}after{_BOM}"
    assert strip_control(raw) == "beforemiddleafter"


def test_strip_control_flattens_newlines_and_trims_fields():
    assert strip_control("  line one\r\nline two  ") == "line one  line two"


def test_sanitize_terminal_text_caps_output_after_stripping():
    text = sanitize_terminal_text(_ANSI + "x" * 300, max_len=20)
    assert "\x1b" not in text
    assert len(text) == 20
    assert text.endswith("…")


def test_sanitize_terminal_line_preserves_indentation():
    assert sanitize_terminal_line("  path: .cursor/mcp.json") == "  path: .cursor/mcp.json"


def test_escape_markdown_strips_controls_before_escaping():
    escaped = escape_markdown(f"evil{_ANSI}*name*{_BIDI}")
    assert "\x1b" not in escaped
    assert _BIDI not in escaped
    assert r"\*name\*" in escaped


def test_render_check_never_emits_terminal_controls(tmp_path: Path):
    root = tmp_path / "repo"
    cfg = root / ".cursor"
    cfg.mkdir(parents=True)
    name = f"evil{_ANSI}{_BIDI}component"
    (cfg / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    name: {
                        "command": "npx",
                        "args": ["-y", "@demo/evil"],
                        "env": {"TOKEN": "x"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    report, cards, _scan = build_check_report(root)
    text = render_check(report, cards)
    assert "\x1b" not in text
    assert _BIDI not in text
    assert "component" in text

    why_lines, code = why_repo("component", root=root)
    assert code == 0
    why_text = "\n".join(why_lines)
    assert "\x1b" not in why_text
    assert _BIDI not in why_text


def test_render_gate_report_sanitizes_delta_lines():
    text = render_gate_report(
        {
            "verdict": "NEEDS_REVIEW",
            "label": "GROWTH",
            "lines": [f'+ mcp "evil{_ANSI}{_BIDI}name" @ .cursor/mcp.json'],
        }
    )
    assert "\x1b" not in text
    assert _BIDI not in text
    assert "evilname" in text
