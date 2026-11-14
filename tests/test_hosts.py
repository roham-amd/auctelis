from pathlib import Path

from auctelis.hosts.profiles import get_host_profile, list_host_profiles
from auctelis.inventory.collector import collect_inventory


def test_host_profiles_include_cursor_and_claude():
    ids = {p["host_id"] for p in list_host_profiles()}
    assert "cursor" in ids
    assert "claude-code" in ids
    cursor = get_host_profile("cursor")
    assert cursor is not None
    assert cursor.support == "PARTIAL"
    assert any(s.permission_kind == "declared" for s in cursor.config_surfaces)


def test_discover_cursor_host_declared_only():
    root = Path(__file__).resolve().parents[1] / "tests" / "hosts" / "fixtures" / "cursor-declared"
    inv = collect_inventory(root)
    hosts = [c for c in inv.components if c.get("type") == "Agent Host"]
    assert any(c.get("host_id") == "cursor" for c in hosts)
    cursor = next(c for c in hosts if c.get("host_id") == "cursor")
    assert cursor.get("permission_scope") == "DECLARED_ONLY"
    assert cursor.get("effective_permissions") == "NOT VERIFIED"


def test_discover_claude_code_host():
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "hosts"
        / "fixtures"
        / "claude-code-declared"
    )
    inv = collect_inventory(root)
    hosts = [c for c in inv.components if c.get("type") == "Agent Host"]
    assert any(c.get("host_id") == "claude-code" for c in hosts)


def test_no_host_markers():
    root = Path(__file__).resolve().parents[1] / "tests" / "hosts" / "fixtures" / "no-host-markers"
    inv = collect_inventory(root)
    hosts = [c for c in inv.components if c.get("type") == "Agent Host"]
    assert hosts == []
