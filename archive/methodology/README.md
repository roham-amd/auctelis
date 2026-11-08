# Archived methodology kit

Moved out of the product path in Guard **3.6** / **authdiff**.

| Path | Former root location |
| --- | --- |
| `prompts/` | `/prompts` |
| `modules/` | `/modules` |
| `control-packs/` | `/control-packs` |
| `kit/` | `/kit` |

These are **optional deep-assessment** materials (procedure 1.0). They are not
required for `authdiff doctor` / `open` / `scan` / the Authority Diff Action.

Rebuild the monolith (maintainers only):

```bash
cd tools && uv run authdiff build prompts --write
```

Output still lands at `archive/methodology/prompts/audit.full.md`.
