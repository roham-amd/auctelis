# Contributing to auctelis

Thanks for helping improve **auctelis**.

Product contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Roadmap:
[`docs/ROADMAP.md`](docs/ROADMAP.md) · Docs index:
[`docs/DOCUMENTATION-INDEX.md`](docs/DOCUMENTATION-INDEX.md).

Prioritize Trust Dossier (`inspect`) + Authority Diff (`diff --base`) work over
advanced/experimental surfaces.

## Development setup

```bash
cd tools
uv sync --all-packages --locked   # product + tools/dev (auctelis-dev)
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
  Docker install images were removed — use the git-tag / PyPI install story.
- Product CLI name is **`auctelis`** (sole console script in the wheel). Maintainer
  commands live on **`auctelis-dev`** via the source-only workspace member
  `tools/dev/` (`auctelis-devtools`).
- Keep the product path lean: `inspect` → `inspect --local` → `diff --base`.
  Legacy lockfile / gate / fleet commands (`check`, `lock`, `gate`, `init`,
  `status`, `trust`, `why`, `demo`) live on `auctelis-dev` only. Host tripwires
  and public `scan` / `vet` / `explain` CLIs are removed; annotation helpers
  live on `auctelis-dev`. The `docs/pilots/` tracker is intentional for the
  dossier-first kill criterion.
- Passive inventory must remain read-only. Maintainer opt-in execute paths
  (`auctelis-dev run`, `snapshot --execute`) scrub env only and must document
  sandbox limits.
- Architecture: `inspect_target` / `local_hosts` / `export/dossier` (Trust
  Dossier) and `lock_io` → `authority_lock` → `reach_tiers` → `authority_card`
  → `export/pr_comment` → `gate` / `diff_base` (Authority Diff). Core rules,
  `artifact_vet`, and `typosquat` live in `auctelis.security` (shipped in the
  wheel). Do not pull the research scanner (`auctelis_research`) into the
  product gate path. Renderers must never invent evidence, hosts, or approvals.
- CLI: product handlers live in `tools/auctelis/cli/dispatch.py` /
  `inspect_cmd.py`; maintainer / research handlers live in
  `tools/dev/auctelis_devtools/` and are reached only via `auctelis-dev`. Keep
  `auctelis_research` imports lazy and behind `require_research()` so the
  product wheel never depends on them.
- Security: validate external URLs before `urlopen`; resolve executables with
  `shutil.which`; pass subprocess argv lists (never `shell=True`); keep target
  strings escaped before markdown/terminal output. Exception: pasteable
  **Pin fix** snippets use `markdown_code_span` (literal code span, omit when
  over budget or multiline) so reviewers can copy them into MCP config.
- Trusted destinations are authority: in the gate they are honored only when
  `.auctelis/trusted-hosts` is CODEOWNERS-covered.

## Pull requests

- Prefer small, reviewable PRs.
- Update `CHANGELOG.md` for user-visible changes.
- Keep `VERSION`, `canonical/versions.json`, `canonical/release-manifest.json`,
  `tools/pyproject.toml`, `tools/auctelis/__init__.py`, `tools/auctelis/versioning.py`
  embeds, and install/Action pins (`@vX.Y.Z`) aligned when cutting a release.
  Run `auctelis-dev build all` to sync packaged metadata and the demo fixture.
