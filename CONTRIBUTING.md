# Contributing to auctelis

Thanks for helping improve **auctelis** (product line formerly branded auctelis).

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
- Docker: [`Dockerfile`](Dockerfile) pins `python:3.12.16-slim-trixie@sha256:…` + `ghcr.io/astral-sh/uv:…@sha256:…`; `uv sync --locked --no-dev`.
- Actions: full commit SHAs with version comments; CI uses `uv python install 3.12.16` + `uv sync --locked` + `uv run --locked …`.
- Product CLI name is **`auctelis`**; keep **`auctelis`** as a console-script alias. Maintainer commands live on **`auctelis-dev`**.
- Research/archive trees (`archive/`, `kit/`, atlas) were removed in 0.3.0 — keep the product path lean (lock + gate + doctor). The `docs/pilots/` tracker is intentional for the five-repo kill criterion.
- Passive scans must remain read-only. Opt-in execute paths (`run`, `snapshot --execute`) scrub env only and must document sandbox limits.
- Lock I/O lives in `auctelis.lock_io`; lock build/diff in `auctelis.authority_lock`. Do not pull the scanner into the broker path.

## Pull requests

- Prefer small, reviewable PRs.
- Update `CHANGELOG.md` for user-visible changes.
- Keep `VERSION`, `canonical/versions.json`, `canonical/release-manifest.json`,
  `tools/pyproject.toml`, `tools/auctelis/__init__.py`, `tools/auctelis/versioning.py`
  embeds, and install/Action pins (`@vX.Y.Z`) aligned when cutting a release.
  Run `auctelis-dev build all` to sync packaged metadata and the demo fixture.
