"""Minimal AUTHORITY.yml language-server stub (stdio JSON-RPC skeleton).

Not a full LSP. Validates AUTHORITY.yml / AUTHORITY.lock against shipped JSON
Schemas and prints diagnostics. Enough to wire an editor later.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from authdiff.paths import repo_root


def _schema_path(name: str) -> Path:
    packaged = Path(__file__).resolve().parent / "data" / name
    if packaged.is_file():
        return packaged
    return repo_root() / "schemas" / name


def validate_authority_doc(path: Path) -> list[dict[str, Any]]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return [{"severity": "error", "message": "jsonschema not installed"}]

    text = path.read_text(encoding="utf-8")
    # Tiny YAML→JSON for the subset we care about: reuse JSON if possible.
    data: Any
    if path.suffix.lower() == ".json" or path.name.endswith(".lock.json"):
        data = json.loads(text)
        schema_file = "authority-lock.schema.json"
    else:
        # Accept JSON-in-YAML-file for the stub; full YAML needs PyYAML later.
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return [
                {
                    "severity": "warning",
                    "message": (
                        "LSP stub parses JSON only today; rename to AUTHORITY.lock.json "
                        "or install a YAML-capable build."
                    ),
                    "line": 1,
                }
            ]
        schema_file = (
            "authority-lock.schema.json"
            if "mcp_tools" in data or path.name.upper().startswith("AUTHORITY.LOCK")
            else "authority-policy.schema.json"
        )

    schema = json.loads(_schema_path(schema_file).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    diags: list[dict[str, Any]] = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        diags.append(
            {
                "severity": "error",
                "message": err.message,
                "path": "/" + "/".join(str(p) for p in err.path),
            }
        )
    return diags


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print("usage: authdiff lsp-validate <AUTHORITY.yml|AUTHORITY.lock.json>")
        return 2
    path = Path(args[0])
    diags = validate_authority_doc(path)
    print(json.dumps({"path": str(path), "diagnostics": diags}, indent=2))
    return 1 if any(d.get("severity") == "error" for d in diags) else 0


if __name__ == "__main__":
    raise SystemExit(main())
