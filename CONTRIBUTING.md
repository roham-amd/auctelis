# Contributing to auctelis

Thanks for helping improve **auctelis**.

Product contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Roadmap:
[`docs/ROADMAP.md`](docs/ROADMAP.md) · Docs index:
[`docs/DOCUMENTATION-INDEX.md`](docs/DOCUMENTATION-INDEX.md).

Prioritize Authority Lock + PR Gate work over advanced/experimental surfaces.

## Development setup

```bash
cd tools
uv sync --locked
uv run auctelis-dev lint --check-format
uv run mypy auctelis
uv run pytest -q ../tests
uv run auctelis-dev build all
uv run pip-audit
```

CI mirrors this in [`.github/workflows/auctelis-validate.yml`](.github/workflows/auctelis-validate.yml)
(plus corpus harness and wheel smoke).

## Conventions

- Python: declare constraints in [`tools/pyproject.toml`](tools/pyproject.toml) via `uv add` / `uv add --dev`; lock exact versions + hashes in [`tools/uv.lock`](tools/uv.lock); interpreter minor in [`tools/.python-version`](tools/.python-version) (`3.12`). Commit all three; ignore `.venv/`.
- Actions: full commit SHAs with version comments; CI uses `uv python install 3.12.16` + `uv sync --locked` + `uv run --locked …`.
  Docker install images were removed in 0.9.0 — use the git-tag / PyPI install story.
- Product CLI name is **`auctelis`**; keep **`auctelis`** as a console-script alias. Maintainer commands live on **`auctelis-dev`**.
- Keep the product path lean: `init --owner` → `check` → `lock --update` → `gate` / `diff` / `why`.
  Host tripwires and public `scan` / `vet` / `explain` CLIs are removed; annotation
  helpers live on `auctelis-dev`. The `docs/pilots/` tracker is intentional for
  the five-slot kill criterion.
- Passive inventory must remain read-only. Maintainer opt-in execute paths
  (`auctelis-dev run`, `snapshot --execute`) scrub env only and must document
  sandbox limits.
- Lock I/O lives in `auctelis.lock_io`; lock build/diff in `auctelis.authority_lock`. Do not pull the scanner into the product gate path.

## Pull requests

- Prefer small, reviewable PRs.
- Update `CHANGELOG.md` for user-visible changes.
- Keep `VERSION`, `canonical/versions.json`, `canonical/release-manifest.json`,
  `tools/pyproject.toml`, `tools/auctelis/__init__.py`, `tools/auctelis/versioning.py`
  embeds, and install/Action pins (`@vX.Y.Z`) aligned when cutting a release.
  Run `auctelis-dev build all` to sync packaged metadata and the demo fixture.
