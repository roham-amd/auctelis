"""Single source of truth for unparsed-config and truncation counts."""

from __future__ import annotations

from auctelis.inventory.coverage import (
    count_truncation_events,
    count_unparsed_agent_configs,
    family_coverage_line_from_coverage,
    summarize_coverage,
    truncation_honesty_notes,
    unparsed_agent_config_count_from_coverage,
)
from auctelis.security.decision import (
    unparsed_agent_config_count as decision_unparsed_count,
)


def test_unparsed_markers_match_case_and_separators():
    events = [
        {"type": "parse_error", "path": "skills/foo/SKILL.md"},
        {"type": "parse_skipped_size", "path": ".cursor\\mcp.json"},
        {"type": "file_too_large", "path": "docs/README.md"},
        None,
    ]
    assert count_unparsed_agent_configs(events) == 2
    # The decision layer delegates to the same implementation.
    assert decision_unparsed_count({}, events) == 2


def test_duplicate_events_for_one_config_count_once():
    events = [
        {"type": "parse_error", "path": ".cursor/mcp.json"},
        {"type": "unparsed_agent_config", "path": ".cursor/mcp.json"},
    ]
    assert count_unparsed_agent_configs(events) == 1


def test_stored_unparsed_count_wins_over_events():
    coverage = {
        "unparsed_agent_config_count": 0,
        "parser_events": [{"type": "parse_error", "path": ".cursor/mcp.json"}],
    }
    assert unparsed_agent_config_count_from_coverage(coverage) == 0
    assert decision_unparsed_count(coverage) == 0
    # Legacy payload: no stored key → count from events.
    assert decision_unparsed_count({"parser_events": coverage["parser_events"]}) == 1


def test_summarize_coverage_keeps_accurate_counts_but_caps_events():
    events = [{"type": "default_exclude"} for _ in range(60)]
    events += [
        {"type": "depth_limit"},
        {"type": "file_limit_reached"},
        {"type": "read_error"},
    ]
    coverage = summarize_coverage([], parser_events=events)
    assert coverage["depth_limit_count"] == 1
    assert coverage["file_limit_reached_count"] == 1
    assert coverage["read_error_count"] == 1
    assert coverage["truncated"] is True
    assert len(coverage["parser_events"]) == 50


def test_honesty_helpers_handle_missing_and_unknown_inputs():
    assert family_coverage_line_from_coverage(None) == "Coverage: (unavailable)"
    assert truncation_honesty_notes(None) == []
    assert truncation_honesty_notes({"read_error_count": 2})
    notes = truncation_honesty_notes({"read_error_count": 2})
    assert any("Read errors" in note for note in notes)
    assert count_truncation_events([None, {"type": "depth_limit"}]) == {
        "depth_limit": 1,
        "file_limit_reached": 0,
        "read_error": 0,
    }
    coverage = summarize_coverage([{"adapter_maturity": "EXPERIMENTAL"}])
    assert coverage["component_counts_by_maturity"]["EXPERIMENTAL"] == 1
