"""AUCT-046 — ephemeral inventory args for pin doctor (not lock schema)."""

from __future__ import annotations

from types import SimpleNamespace

from auctelis.check import attach_launcher_args, attach_launcher_args_to_delta


def test_attach_launcher_args_copies_inventory_argv():
    scan = SimpleNamespace(
        inventory={
            "components": [
                {
                    "repository_path": ".cursor/mcp.json",
                    "name": "scoped",
                    "args": ["-y", "@scope/mcp", "/workspace"],
                }
            ]
        }
    )
    records = [
        {"path": ".cursor/mcp.json", "name": "scoped", "launcher": "npx"},
        {"path": ".cursor/mcp.json", "name": "other", "launcher": "npx"},
    ]
    attach_launcher_args(records, scan)
    assert records[0]["args"] == ["-y", "@scope/mcp", "/workspace"]
    assert "args" not in records[1]


def test_attach_launcher_args_to_delta_rehydrates_added_and_after():
    records = [
        {
            "path": ".cursor/mcp.json",
            "name": "scoped",
            "args": ["-y", "@scope/mcp", "/workspace"],
        },
        {
            "path": ".cursor/mcp.json",
            "name": "sqlite",
            "args": ["run", "-i", "--rm", "mcp/sqlite:latest"],
        },
    ]
    delta = {
        "changes": {
            "added": [
                {
                    "path": ".cursor/mcp.json",
                    "name": "scoped",
                    "launcher": "npx",
                    "package_stem": "@scope/mcp",
                }
            ],
            "changed": [
                {
                    "after": {
                        "path": ".cursor/mcp.json",
                        "name": "sqlite",
                        "launcher": "docker",
                        "package_stem": "mcp/sqlite",
                    }
                }
            ],
            "removed": [],
        }
    }
    attach_launcher_args_to_delta(delta, records)
    assert delta["changes"]["added"][0]["args"] == ["-y", "@scope/mcp", "/workspace"]
    assert delta["changes"]["changed"][0]["after"]["args"] == [
        "run",
        "-i",
        "--rm",
        "mcp/sqlite:latest",
    ]


def test_attach_launcher_args_noop_without_scan():
    records = [{"path": "a", "name": "b"}]
    attach_launcher_args(records, None)
    assert records == [{"path": "a", "name": "b"}]
