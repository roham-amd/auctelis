from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from auctelis.paths import (
    canonical_schema_path,
    published_schema_paths,
    repo_root,
    version_file_path,
)
from auctelis.supply_chain.digest import sha256_file
from auctelis.versioning import load_versions as load_canonical_versions
from auctelis_devtools.deps import normalize_package_name


def sync_schemas() -> list[str]:
    """Copy canonical schema to published aliases; return actions."""
    src = canonical_schema_path()
    if not src.is_file():
        raise FileNotFoundError(f"Missing canonical schema: {src}")
    actions: list[str] = []
    for dest in published_schema_paths():
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        if dest.is_file() and dest.read_bytes() == data:
            actions.append(f"unchanged {dest.relative_to(repo_root())}")
        else:
            dest.write_bytes(data)
            actions.append(f"updated {dest.relative_to(repo_root())}")
    actions.extend(sync_authority_schemas())
    return actions


def sync_authority_schemas() -> list[str]:
    """Keep packaged authority schemas aligned with ``schemas/`` (wheel data)."""
    root = repo_root()
    actions: list[str] = []
    data_dir = root / "tools" / "auctelis" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("authority-lock.schema.json", "authority-policy.schema.json"):
        src = root / "schemas" / name
        dest = data_dir / name
        if not src.is_file():
            raise SystemExit(f"Missing schemas/{name}")
        data = src.read_bytes()
        if dest.is_file() and dest.read_bytes() == data:
            actions.append(f"unchanged tools/auctelis/data/{name}")
        else:
            dest.write_bytes(data)
            actions.append(f"updated tools/auctelis/data/{name}")
    return actions


def check_schema_parity() -> None:
    src = canonical_schema_path()
    for dest in published_schema_paths():
        if not dest.is_file():
            raise SystemExit(f"Missing published schema: {dest}")
        if sha256_file(src) != sha256_file(dest):
            raise SystemExit(
                f"Schema drift: {dest} does not match canonical {src}. "
                "Run: auctelis-dev build schemas"
            )
    root = repo_root()
    for name in ("authority-lock.schema.json", "authority-policy.schema.json"):
        src = root / "schemas" / name
        dest = root / "tools" / "auctelis" / "data" / name
        if not dest.is_file():
            raise SystemExit(f"Missing packaged schema: {dest}")
        if sha256_file(src) != sha256_file(dest):
            raise SystemExit(
                f"Schema drift: {dest} does not match schemas/{name}. "
                "Run: auctelis-dev build schemas"
            )


def check_requires_python() -> None:
    pyproject = (repo_root() / "tools" / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^requires-python\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not match:
        raise SystemExit("tools/pyproject.toml missing requires-python")
    required = match.group(1).strip()
    if required != ">=3.12":
        raise SystemExit(
            f"tools/pyproject.toml requires-python must be '>=3.12' (found {required!r})"
        )


def sync_packaged_version_metadata() -> list[str]:
    """Keep wheel-bundled VERSION / versions / release-manifest aligned with canonical."""
    root = repo_root()
    data_dir = root / "tools" / "auctelis" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    actions: list[str] = []

    product = (root / "VERSION").read_text(encoding="utf-8").strip() + "\n"
    product_bytes = product.encode("utf-8")
    packaged_version = data_dir / "VERSION"
    if not packaged_version.is_file() or packaged_version.read_bytes() != product_bytes:
        packaged_version.write_bytes(product_bytes)
        actions.append("updated tools/auctelis/data/VERSION")
    else:
        actions.append("unchanged tools/auctelis/data/VERSION")

    for name in ("versions.json", "release-manifest.json"):
        src = root / "canonical" / name
        dest = data_dir / name
        if not src.is_file():
            raise SystemExit(f"Missing canonical/{name}")
        src_bytes = src.read_bytes()
        if not dest.is_file() or dest.read_bytes() != src_bytes:
            dest.write_bytes(src_bytes)
            actions.append(f"updated tools/auctelis/data/{name}")
        else:
            actions.append(f"unchanged tools/auctelis/data/{name}")
    actions.extend(sync_demo_fixture())
    return actions


# Checkout paths → package paths. Dot-directories are excluded from wheels by
# setuptools, so packaged fixtures use non-hidden names and demo materializes
# them back to ``.cursor`` / ``.github`` at runtime.
_DEMO_FIXTURE_MAP: tuple[tuple[Path, Path], ...] = (
    (Path("README.md"), Path("README.md")),
    (Path("skills") / "bootstrap" / "SKILL.md", Path("skills") / "bootstrap" / "SKILL.md"),
    (Path(".cursor") / "mcp.json", Path("cursor") / "mcp.json"),
    (Path(".github") / "workflows" / "agent.yml", Path("github") / "workflows" / "agent.yml"),
)


def sync_demo_fixture() -> list[str]:
    """Keep packaged ``auctelis demo`` fixture aligned with ``examples/demo-vulnerable``."""
    import shutil

    root = repo_root()
    src_root = root / "examples" / "demo-vulnerable"
    dest_root = root / "tools" / "auctelis" / "data" / "demo-vulnerable"
    if not src_root.is_dir():
        raise SystemExit("Missing examples/demo-vulnerable")
    actions: list[str] = []
    for src_rel, dest_rel in _DEMO_FIXTURE_MAP:
        src = src_root / src_rel
        dest = dest_root / dest_rel
        if not src.is_file():
            raise SystemExit(
                f"Missing demo fixture file: examples/demo-vulnerable/{src_rel.as_posix()}"
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        if dest.is_file() and dest.read_bytes() == data:
            actions.append(f"unchanged tools/auctelis/data/demo-vulnerable/{dest_rel.as_posix()}")
        else:
            dest.write_bytes(data)
            actions.append(f"updated tools/auctelis/data/demo-vulnerable/{dest_rel.as_posix()}")
    for legacy in (dest_root / ".cursor", dest_root / ".github"):
        if legacy.exists():
            shutil.rmtree(legacy)
            actions.append(f"removed legacy {legacy.relative_to(root).as_posix()}")
    return actions


def check_demo_fixture_parity() -> None:
    root = repo_root()
    src_root = root / "examples" / "demo-vulnerable"
    dest_root = root / "tools" / "auctelis" / "data" / "demo-vulnerable"
    for src_rel, dest_rel in _DEMO_FIXTURE_MAP:
        src = src_root / src_rel
        dest = dest_root / dest_rel
        if not dest.is_file():
            raise SystemExit(
                "Missing packaged demo fixture: "
                f"tools/auctelis/data/demo-vulnerable/{dest_rel.as_posix()}. "
                "Run: auctelis-dev build all"
            )
        if sha256_file(src) != sha256_file(dest):
            raise SystemExit(
                f"Demo fixture drift: {dest} does not match {src}. Run: auctelis-dev build all"
            )
    _assert_demo_tier2_ci(src_root)


def _assert_demo_tier2_ci(src_root: Path) -> None:
    """AUCT-042: the public demo must still showcase a tier-2 agent CI step."""
    from auctelis.check import build_check_report

    report, _cards, _scan = build_check_report(src_root)
    reach = report.get("reach") if isinstance(report, dict) else None
    records = (reach or {}).get("records") if isinstance(reach, dict) else None
    tier2_ci = [
        rec
        for rec in (records or [])
        if isinstance(rec, dict)
        and str(rec.get("kind") or "") == "ci"
        and int(rec.get("tier") or 0) >= 2
    ]
    if tier2_ci:
        return
    counts = (reach or {}).get("tier_counts") if isinstance(reach, dict) else {}
    raise SystemExit(
        "examples/demo-vulnerable must yield at least one tier-2 CI record "
        f"(tier_counts={counts}). agent.yml needs a command-position agent step."
    )


_REVERSED_CUTOVER_RE = re.compile(
    r"(?i)(?:\bpublish\b|\bworkflow_dispatch\b)[\s\S]{0,180}?\bthen\s+flip\b"
)
_CUTOVER_STEPS = (
    re.compile(r"(?m)^1\.\s+Claim\b"),
    re.compile(r"(?m)^2\.\s+Bump\+flip\b"),
    re.compile(r"(?m)^3\.\s+Publish\b"),
    re.compile(r"(?m)^4\.\s+Live probe\b"),
    re.compile(r"(?m)^5\.\s+Tag\b"),
)


def _check_recruitment_cutover_order() -> str:
    """Reject publish-before-flip instructions in the pilot recruitment doc."""
    path = repo_root() / "docs" / "pilots" / "RECRUITMENT.md"
    if not path.is_file():
        return "note: RECRUITMENT.md absent — cutover-order text not checked"
    text = path.read_text(encoding="utf-8")
    discusses_cutover = any(
        token in text for token in ("pypi_live", "PyPI readiness", "workflow_dispatch", "Bump+flip")
    )
    if not discusses_cutover:
        return "note: RECRUITMENT.md has no PyPI cutover section — order not checked"
    if _REVERSED_CUTOVER_RE.search(text):
        raise SystemExit(
            "RECRUITMENT.md reverses PyPI cutover order (publish … then flip). "
            "Required: claim → bump+flip PR → publish → live probe → tag."
        )
    positions: list[int] = []
    for step in _CUTOVER_STEPS:
        match = step.search(text)
        if match is None:
            raise SystemExit(
                "RECRUITMENT.md is missing a numbered PyPI cutover step "
                "(1. Claim, 2. Bump+flip, 3. Publish, 4. Live probe, 5. Tag)."
            )
        positions.append(match.start())
    if positions != sorted(positions):
        raise SystemExit(
            "RECRUITMENT.md PyPI cutover steps are out of order "
            "(required: claim → bump+flip → publish → live probe → tag)."
        )
    if "git+…" in text or "git+..." in text:
        raise SystemExit(
            "RECRUITMENT.md still has a truncated git+ install command; "
            "paste the full uvx --from URL."
        )
    return "ok RECRUITMENT.md cutover order is claim → bump+flip → publish → live probe → tag"


def _check_embedded_version_fallbacks(product: str, versions: dict[str, str]) -> None:
    """Wheel-only fallbacks must not drift from canonical metadata."""
    from auctelis.versioning import _EMBEDDED_PRODUCT_VERSION, _EMBEDDED_VERSIONS

    if product != _EMBEDDED_PRODUCT_VERSION:
        raise SystemExit(
            f"versioning._EMBEDDED_PRODUCT_VERSION ({_EMBEDDED_PRODUCT_VERSION}) "
            f"!= VERSION ({product})"
        )
    if dict(_EMBEDDED_VERSIONS) != dict(versions):
        raise SystemExit(
            "versioning._EMBEDDED_VERSIONS is out of sync with canonical/versions.json; "
            "update tools/auctelis/versioning.py"
        )


def check_version_metadata() -> None:
    versions = load_canonical_versions()
    if not isinstance(versions, dict):
        raise SystemExit(f"Invalid versions.json: expected object, got {type(versions).__name__}")
    product = version_file_path().read_text(encoding="utf-8").strip()
    if versions.get("auctelis_product") != product:
        raise SystemExit(
            f"VERSION file ({product}) != canonical/versions.json auctelis_product "
            f"({versions.get('auctelis_product')})"
        )
    _check_embedded_version_fallbacks(product, versions)

    # Keep tooling package metadata aligned with canonical build_tool tag.
    build_tool = str(versions.get("build_tool") or "")
    expected_pkg = build_tool.removeprefix("auctelis-")
    pyproject = (repo_root() / "tools" / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not match:
        raise SystemExit("tools/pyproject.toml missing version")
    if expected_pkg and match.group(1) != expected_pkg:
        raise SystemExit(
            f"tools/pyproject.toml version ({match.group(1)}) != "
            f"canonical build_tool package version ({expected_pkg})"
        )

    init_text = (repo_root() / "tools" / "auctelis" / "__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    if not init_match:
        raise SystemExit("tools/auctelis/__init__.py missing __version__")
    if expected_pkg and init_match.group(1) != expected_pkg:
        raise SystemExit(
            f"tools/auctelis/__init__.py __version__ ({init_match.group(1)}) != "
            f"canonical build_tool package version ({expected_pkg})"
        )
    product_match = re.search(r'__product_version__\s*=\s*"([^"]+)"', init_text)
    if not product_match:
        raise SystemExit("tools/auctelis/__init__.py missing __product_version__")
    if product_match.group(1) != product:
        raise SystemExit(
            f"tools/auctelis/__init__.py __product_version__ ({product_match.group(1)}) != "
            f"VERSION ({product})"
        )

    packaged_version = (
        (repo_root() / "tools" / "auctelis" / "data" / "VERSION")
        .read_text(encoding="utf-8")
        .strip()
    )
    if packaged_version != product:
        raise SystemExit(
            f"tools/auctelis/data/VERSION ({packaged_version}) != root VERSION ({product})"
        )

    # Release-blocking: release-manifest must agree with VERSION + package version.
    manifest_path = repo_root() / "canonical" / "release-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("Missing canonical/release-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("product_version") != product:
        raise SystemExit(
            f"release-manifest product_version ({manifest.get('product_version')}) != "
            f"VERSION ({product})"
        )
    if expected_pkg and manifest.get("package_version") != expected_pkg:
        raise SystemExit(
            f"release-manifest package_version ({manifest.get('package_version')}) != "
            f"canonical build_tool package version ({expected_pkg})"
        )
    for key in ("findings_contract", "baseline_contract", "rule_pack", "policy_contract"):
        if key in versions and manifest.get("contracts", {}).get(key) != versions.get(key):
            raise SystemExit(
                f"release-manifest contracts.{key} "
                f"({manifest.get('contracts', {}).get(key)}) != "
                f"versions.json {key} ({versions.get(key)})"
            )

    interfaces = manifest.get("interfaces") or {}
    for dead_alias in ("open_alias", "fix_alias"):
        if interfaces.get(dead_alias) is True:
            raise SystemExit(
                f"release-manifest interfaces.{dead_alias} must be false "
                "(commands removed; do not advertise enabled aliases)"
            )

    check_install_doc_versions(product)
    check_public_install_versions(product)
    check_bare_command_docs()
    check_policy_schema_contract()


# First-run docs must agree on one install command. Anything else multiplies the
# number of "valid first steps" before the user ever sees the product.
_FIRST_RUN_DOCS = (
    "README.md",
    "docs/INSTALL.md",
    "docs/AUCTELIS-GATE.md",
    "docs/PLAYBOOK.md",
    "skills/auctelis-auditor/SKILL.md",
)

# Every public doc that may name an install pin. A stale tag/PyPI pin is a trust
# hit before the first command runs, so the build fails on it.
_INSTALL_DOCS = (
    *_FIRST_RUN_DOCS,
    "docs/CLI-REFERENCE.md",
    "docs/PRODUCT.md",
    "docs/ROADMAP.md",
    "docs/SECURITY-RULES.md",
    "docs/DOCUMENTATION-INDEX.md",
    "docs/pilots/RECRUITMENT.md",
    "docs/pilots/TRACKER.md",
    "docs/auctelis-consumer-gate.example.yml",
    "docs/auctelis-org-audit.yml",
    "tools/README.md",
    "SECURITY.md",
)

_GIT_TAG_PIN_RE = re.compile(
    r"git\+https://github\.com/roham-amd/auctelis\.git@v([0-9][0-9A-Za-z.\-]*)"
)
_PACKAGE_PIN_RE = re.compile(r"auctelis==([0-9][0-9A-Za-z.\-]*)")


def _pypi_live() -> bool:
    """Read ``pypi_live`` via build ``repo_root`` (monkeypatch-friendly for tests).

    Product runtime uses ``auctelis.versioning.pypi_live`` (cached, wheel-safe).
    Build checks must follow ``repo_root()`` so install-doc tests can point at
    a fake tree without clearing the versioning cache.
    """
    manifest_path = repo_root() / "canonical" / "release-manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(data.get("pypi_live"))


def check_public_install_versions(product: str) -> None:
    """Public install blocks must name a command that works at this release.

    When ``pypi_live`` is true, first-run docs require bare ``uvx auctelis``.
    When false, they require the pinned ``uvx --from git+…@v<current>`` form and
    must not promise unqualified ``uvx auctelis`` as if PyPI already works.
    Any ``git+…@vX`` or ``auctelis==X`` pin must match the current product version.
    """
    root = repo_root()
    pypi_live = _pypi_live()
    for rel in _INSTALL_DOCS:
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"Missing public install doc: {rel}")
        text = path.read_text(encoding="utf-8")
        for regex, label in (
            (_GIT_TAG_PIN_RE, "git-tag pin"),
            (_PACKAGE_PIN_RE, "package pin"),
        ):
            for match in regex.finditer(text):
                found = match.group(1)
                if found != product:
                    raise SystemExit(
                        f"{rel} pins {label} {found!r} but VERSION is {product!r}; "
                        "update the install docs and the release pin together"
                    )

    bare_promise = re.compile(r"(?<![\w\-])uvx auctelis(?!\S)")
    bare_check = re.compile(r"(?<![\w\-])uvx auctelis check\b")
    git_from = re.compile(r"uvx\s+--from\s+[\"']?git\+")
    once_published = re.compile(r"once\s+(?:published|PyPI|pypi)", re.IGNORECASE)
    for rel in _FIRST_RUN_DOCS:
        text = (root / rel).read_text(encoding="utf-8")
        if pypi_live:
            bare_m = bare_check.search(text)
            if bare_m is None:
                raise SystemExit(
                    f"{rel} must show `uvx auctelis check` as the first-run install "
                    "(pypi_live=true in release-manifest)"
                )
            git_m = git_from.search(text)
            if git_m is not None and git_m.start() < bare_m.start():
                raise SystemExit(
                    f"{rel} must lead with bare `uvx auctelis check` before any "
                    "`uvx --from git+…` fallback (pypi_live=true)"
                )
            # Awkward parenthetical workarounds next to the primary install.
            if rel == "docs/AUCTELIS-GATE.md" and re.search(
                r"uvx auctelis check\s*\([^)]*INSTALL",
                text,
            ):
                raise SystemExit(
                    f"{rel} must not wrap the primary install in a parenthetical "
                    "INSTALL.md workaround when pypi_live=true"
                )
            continue
        if "uvx --from" not in text:
            raise SystemExit(f"{rel} must show `uvx --from git+…@v{product}` while pypi_live=false")
        # Unqualified bare uvx auctelis as a working command is a false promise.
        for match in bare_promise.finditer(text):
            window = text[max(0, match.start() - 80) : match.end() + 80]
            if once_published.search(window):
                raise SystemExit(
                    f"{rel} still defers `uvx auctelis` with 'once published' copy; "
                    "while pypi_live=false document the git-tag install as primary"
                )
            # Bare command without a clear "not yet" qualifier next to it.
            lowered = window.lower()
            if (
                "not yet" not in lowered
                and "when pypi" not in lowered
                and "pypi_live" not in lowered
                and "git+" not in window
                and "--from" not in window
            ):
                raise SystemExit(
                    f"{rel} promises bare `uvx auctelis` but pypi_live=false; "
                    "use the git-tag pin as the primary install command"
                )


def check_install_doc_versions(product: str) -> None:
    """INSTALL.md / CLI-REFERENCE.md version headers must match root VERSION."""
    install = repo_root() / "docs" / "INSTALL.md"
    text = install.read_text(encoding="utf-8")
    for label in ("Product (`VERSION`)", "Package `auctelis`"):
        match = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([^\s|]+)\s*\|", text)
        if not match:
            raise SystemExit(f"docs/INSTALL.md missing version row for {label}")
        if match.group(1) != product:
            raise SystemExit(f"docs/INSTALL.md {label} is {match.group(1)!r}, expected {product!r}")

    cli_ref = repo_root() / "docs" / "CLI-REFERENCE.md"
    cli_text = cli_ref.read_text(encoding="utf-8")
    # e.g. Package `auctelis` **X.Y.Z** · product **X.Y.Z**
    pkg = re.search(r"Package\s+`auctelis`\s+\*\*([^*]+)\*\*", cli_text)
    prod = re.search(r"product\s+\*\*([^*]+)\*\*", cli_text, re.IGNORECASE)
    if not pkg or not prod:
        raise SystemExit(
            "docs/CLI-REFERENCE.md missing Package/product version header "
            "(expected: Package `auctelis` **X** · product **X**)"
        )
    if pkg.group(1).strip() != product:
        raise SystemExit(
            f"docs/CLI-REFERENCE.md package version is {pkg.group(1)!r}, expected {product!r}"
        )
    if prod.group(1).strip() != product:
        raise SystemExit(
            f"docs/CLI-REFERENCE.md product version is {prod.group(1)!r}, expected {product!r}"
        )


def check_bare_command_docs() -> None:
    """Public docs must describe bare CLI → check, not scan-only or watch-only."""
    root = repo_root()
    stale_scan = re.compile(
        r"bare\s+`auctelis`[^.?\n]{0,80}defaults to\s+`?(?:auctelis\s+)?scan",
        re.IGNORECASE,
    )
    stale_watch = re.compile(
        r"bare\s+`auctelis`[^.?\n]{0,100}runs\s+`watch`",
        re.IGNORECASE,
    )
    # SECURITY.md / GUARD-SCAN must not sell Authority Watch as the product.
    stale_product = re.compile(
        r"(?:is\s+\*\*Authority Watch\*\*|Recommended first command[^\n]*:\s*\n\s*auctelis watch)",
        re.IGNORECASE,
    )
    stale_rebrand = re.compile(
        r"formerly branded",
        re.IGNORECASE,
    )
    for rel in (
        "docs/INSTALL.md",
        "docs/CLI-REFERENCE.md",
        "docs/GUARD-SCAN.md",
        "docs/AUCTELIS-GATE.md",
        "docs/AUTHORITY-LOCK.md",
        "tools/README.md",
        "README.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
    ):
        path = root / rel
        text = path.read_text(encoding="utf-8")
        if stale_scan.search(text):
            raise SystemExit(
                f"{rel} still claims bare auctelis defaults only to scan; "
                "document check (repo authority) as the front door"
            )
        if stale_watch.search(text):
            raise SystemExit(
                f"{rel} still claims bare auctelis runs watch; "
                "document check (repo authority) as the front door"
            )
        if rel in {"SECURITY.md", "docs/GUARD-SCAN.md"} and stale_product.search(text):
            raise SystemExit(
                f"{rel} still describes Authority Watch / watch-first as the product; "
                "document check → diff --base → init / lockless workflow → gate"
            )
        if rel == "CONTRIBUTING.md" and stale_rebrand.search(text):
            raise SystemExit(f"{rel} still contains rebrand residue ('formerly branded')")


def check_policy_schema_contract() -> None:
    """Published policy schema must describe fields load_policy actually reads."""
    schema_path = repo_root() / "schemas" / "authority-policy.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    policy_props = (schema.get("properties") or {}).get("policy", {}).get("properties") or {}
    required = {
        "mode",
        "fail_on",
        "output_dir",
        "baseline",
        "require_review",
        "ignore",
    }
    missing = required - set(policy_props)
    if missing:
        raise SystemExit(f"authority-policy.schema.json missing runtime fields: {sorted(missing)}")
    for obsolete in (
        "allow_project_mcp_auto_approve",
        "allow_base_url_overrides",
        "allow_unpinned_launchers",
        "max_unparsed_agent_configs",
    ):
        if obsolete in policy_props:
            raise SystemExit(
                f"authority-policy.schema.json still declares obsolete field {obsolete!r}"
            )
    if "owners" in (schema.get("properties") or {}):
        raise SystemExit(
            "authority-policy.schema.json must not declare top-level owners "
            "(CODEOWNERS is the ownership surface)"
        )
    Draft202012Validator.check_schema(schema)
    example = {
        "version": 1,
        "policy": {
            "mode": "enforce",
            "fail_on": "high",
            "output_dir": "auctelis-out",
            "baseline": ".auctelis/baseline.json",
            "require_review": ["remote_mcp_endpoint"],
            "ignore": [
                {
                    "rule": "AUCTELIS-RULE-003",
                    "path": "examples/**",
                    "justification": "fixture",
                    "owner": "security-team",
                    "expires": "2027-06-01",
                }
            ],
        },
    }
    errors = sorted(
        Draft202012Validator(schema).iter_errors(example),
        key=lambda e: list(e.path),
    )
    if errors:
        msgs = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
        raise SystemExit(f"policy schema rejected canonical example shape: {msgs}")


def validate_json_schema_document() -> None:
    path = canonical_schema_path()
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


_SKIP_MD_PARTS = frozenset(
    {
        ".venv",
        "venv",
        "node_modules",
        "site-packages",
        ".git",
        "auctelis-independent-assessment",
        "archive",  # historical methodology; links may be relative to old roots
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".ruff-cache",
        ".uv-cache",
        "dist",
        "build",
    }
)


def _skip_markdown_path(path: Path) -> bool:
    if _SKIP_MD_PARTS.intersection(path.parts):
        return True
    return any(
        part == "auctelis-out"
        or part.startswith("auctelis-out-")
        or part.startswith("pytest-of-")
        or part in {".tmp-uv", "auctelis-pytest"}
        for part in path.parts
    )


def check_internal_markdown_links() -> list[str]:
    root = repo_root()
    checked: list[str] = []
    for md in sorted(root.rglob("*.md")):
        if _skip_markdown_path(md):
            continue
        text = md.read_text(encoding="utf-8")
        for target in _LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (md.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                raise SystemExit(f"Broken link in {md.relative_to(root)}: {target}")
        checked.append(str(md.relative_to(root)))
    return checked


def check_dependency_pins() -> list[str]:
    """Ensure ``uv.lock`` is in sync and satisfies declared ``pyproject.toml`` constraints."""
    from auctelis_devtools.deps import (
        ensure_lock_in_sync,
        parse_declared_requirements,
        parse_lock_pins,
    )

    ensure_lock_in_sync()
    lock = parse_lock_pins()
    normalized = {normalize_package_name(name): ver for name, ver in lock.items()}

    try:
        from packaging.requirements import Requirement
        from packaging.version import Version
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(f"packaging is required for pin checks: {exc}") from exc

    actions: list[str] = [f"ok uv.lock present ({len(lock)} packages)"]
    for req in parse_declared_requirements():
        key = normalize_package_name(req.name)
        locked = normalized.get(key)
        if locked is None:
            raise SystemExit(f"declared requirement {req} missing from uv.lock")
        if req.specifier and not req.specifier.contains(Version(locked), prereleases=True):
            raise SystemExit(f"uv.lock {key}=={locked} does not satisfy {req}")
        actions.append(f"ok {req} -> {locked}")

    # Declared requirement compatibility among locked packages (subset used by auctelis).
    declared: dict[str, list[str]] = {
        "jsonschema": [
            "attrs>=22.2.0",
            "jsonschema-specifications>=2023.03.6",
            "referencing>=0.28.4",
            "rpds-py>=0.25.0",
        ],
        "jsonschema-specifications": ["referencing>=0.31.0"],
        "referencing": ["attrs>=22.2.0", "rpds-py>=0.7.0"],
        "pytest": [
            "iniconfig>=2",
            "packaging>=24",
            "pluggy>=1.6,<2",
            "pygments>=2.15",
        ],
    }

    for parent, reqs in declared.items():
        for raw in reqs:
            req = Requirement(raw)
            key = normalize_package_name(req.name)
            pinned = normalized.get(key)
            if pinned is None:
                raise SystemExit(f"uv.lock missing {key} required by {parent}")
            if not req.specifier.contains(Version(pinned), prereleases=True):
                raise SystemExit(
                    f"collision: {parent} needs {raw}, but uv.lock pins {key}=={pinned}"
                )
        actions.append(f"ok {parent} requirements satisfied by uv.lock")

    return actions


def check_wheel_omits_research() -> list[str]:
    """Fail the build if the product wheel still ships the research scanner."""
    import zipfile

    from auctelis.versioning import product_version

    # tools/dev/auctelis_devtools/build.py → tools/dist
    dist = Path(__file__).resolve().parents[2] / "dist"
    if not dist.is_dir():
        return ["skip wheel research check (no dist/*.whl; run uv build first)"]
    ver = product_version()
    matching = sorted(dist.glob(f"auctelis-{ver}-*.whl"))
    # Prefer the wheel for the current product version; never pick a stale
    # lexicographic neighbor (e.g. 0.1.1 after 0.2.0).
    wheel = matching[-1] if matching else None
    if wheel is None:
        wheels = sorted(dist.glob("auctelis-*.whl"))
        if not wheels:
            return ["skip wheel research check (no dist/*.whl; run uv build first)"]
        wheel = wheels[-1]
    banned = (
        # Research package (separate import root; source-checkout only).
        "auctelis_research/",
        # Maintainer package (separate import root; source-checkout only).
        "auctelis_devtools/",
        # AUCT-016: source-only modules that used to ride in the product wheel.
        "auctelis/security/report.py",
        "auctelis/security/baseline.py",
        "auctelis/process_env.py",
        "auctelis/pins.py",
    )
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    hits = [b for b in banned if any(b in n for n in names)]
    if hits:
        raise SystemExit(f"{wheel.name} still contains maintainer/research modules: {hits}")
    # AUCT-024: pypi_live() reads packaged release-manifest at runtime.
    if not any(n.endswith("auctelis/data/release-manifest.json") for n in names):
        raise SystemExit(f"{wheel.name} missing auctelis/data/release-manifest.json")
    if ver not in wheel.name:
        return [
            f"ok {wheel.name} omits maintainer/research modules "
            f"(warning: expected auctelis-{ver}-*.whl)"
        ]
    return [
        f"ok {wheel.name} omits maintainer/research modules",
        f"ok {wheel.name} ships release-manifest.json",
    ]


def check_action_parity() -> list[str]:
    """AUCT-021: root Marketplace action.yml stays in sync with the legacy subpath."""
    root = repo_root()
    product = (root / "VERSION").read_text(encoding="utf-8").strip()
    root_action = root / "action.yml"
    sub_action = root / ".github" / "actions" / "auctelis-gate" / "action.yml"
    if not root_action.is_file():
        raise SystemExit("Missing root action.yml (required for GitHub Marketplace)")
    if not sub_action.is_file():
        raise SystemExit("Missing .github/actions/auctelis-gate/action.yml")
    root_text = root_action.read_text(encoding="utf-8")
    sub_text = sub_action.read_text(encoding="utf-8")
    if root_text != sub_text:
        raise SystemExit(
            "root action.yml and .github/actions/auctelis-gate/action.yml diverge; "
            "keep them byte-identical (Marketplace + legacy subpath)"
        )
    for key in (
        "\n  path:\n",
        "\n  mode:\n",
        "\n  locked:\n",
        "\n  auctelis-version:\n",
        "\n  install-tools-from:\n",
        "\n  comment-on-none:\n",
    ):
        if key not in root_text:
            raise SystemExit(f"root action.yml missing input{key.strip()!r}")
    if "branding:" not in root_text:
        raise SystemExit("root action.yml missing Marketplace branding:")
    if "icon: shield" not in root_text:
        raise SystemExit("root action.yml branding.icon must be shield")
    if "mode=pypi" not in root_text:
        raise SystemExit("root action.yml missing PyPI fast-path install mode")
    pypi_default = re.search(r'AUCTELIS_PYPI_DEFAULT="(true|false)"', root_text)
    if pypi_default is None:
        raise SystemExit(
            'root action.yml missing AUCTELIS_PYPI_DEFAULT="true|false" '
            "(must match release-manifest.json pypi_live)"
        )
    expected_pypi = "true" if _pypi_live() else "false"
    if pypi_default.group(1) != expected_pypi:
        raise SystemExit(
            f"AUCTELIS_PYPI_DEFAULT={pypi_default.group(1)!r} does not match "
            f"release-manifest.json pypi_live={expected_pypi}"
        )
    # Path filter must stay aligned with watched_paths.PATH_FILTER_GREP.
    from auctelis.inventory.watched_paths import PATH_FILTER_GREP

    grep_m = re.search(r"grep -iE '([^']+)'", root_text)
    if grep_m is None:
        raise SystemExit("root action.yml path_filter grep -iE regex missing")
    if grep_m.group(1) != PATH_FILTER_GREP:
        raise SystemExit(
            "action.yml path_filter regex != auctelis.inventory.watched_paths.PATH_FILTER_GREP"
        )
    pin = f"v{product}"
    uses_re = re.compile(
        r"uses:\s*roham-amd/auctelis(?:/\.github/actions/auctelis-gate)?@(v[^\s#]+)"
    )
    for rel in (
        "tools/auctelis/templates/auctelis-diff.yml",
        "tools/auctelis/templates/auctelis-gate.yml",
        "docs/auctelis-org-reusable.yml",
        "docs/auctelis-consumer-gate.example.yml",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        uses_pins = uses_re.findall(text)
        if not uses_pins:
            raise SystemExit(f"{rel} missing auctelis Action uses: pin")
        if pin not in uses_pins:
            raise SystemExit(f"{rel} Action pin {uses_pins} does not match VERSION {product}")
    return [
        "ok root action.yml Marketplace branding + inputs",
        "ok subpath action.yml input parity",
        f"ok AUCTELIS_PYPI_DEFAULT={expected_pypi} matches pypi_live",
        f"ok workflow templates recognize auctelis@{pin}",
    ]


def _release_manifest_parity() -> list[str]:
    """Packaged manifest, and the built wheel when present, must match canonical.

    ``pypi_live()`` reads the manifest baked into the wheel. A wheel built
    before the flip keeps printing ``git+`` CTAs after publish.
    """
    import zipfile

    from auctelis.versioning import product_version

    root = repo_root()
    canonical_path = root / "canonical" / "release-manifest.json"
    if not canonical_path.is_file():
        raise SystemExit("Missing canonical/release-manifest.json")
    canonical = canonical_path.read_bytes()
    notes: list[str] = []
    packaged = root / "tools" / "auctelis" / "data" / "release-manifest.json"
    if packaged.is_file():
        if packaged.read_bytes() != canonical:
            raise SystemExit(
                "tools/auctelis/data/release-manifest.json != "
                "canonical/release-manifest.json (the wheel would bake the drift)"
            )
        notes.append("ok packaged release-manifest.json matches canonical")
    else:
        notes.append("note: packaged release-manifest.json absent")

    dist = root / "tools" / "dist"
    if not dist.is_dir():
        notes.append("note: wheel manifest assert skipped (no tools/dist)")
        return notes
    ver = product_version()
    matching = sorted(dist.glob(f"auctelis-{ver}-*.whl"))
    if not matching:
        notes.append(f"note: wheel manifest assert skipped (no tools/dist/auctelis-{ver}-*.whl)")
        return notes
    wheel = matching[-1]
    with zipfile.ZipFile(wheel) as zf:
        name = next(
            (
                entry
                for entry in zf.namelist()
                if entry.endswith("auctelis/data/release-manifest.json")
            ),
            "",
        )
        if not name:
            raise SystemExit(f"{wheel.name} missing auctelis/data/release-manifest.json")
        baked = zf.read(name)
    if baked != canonical:
        raise SystemExit(
            f"{wheel.name} auctelis/data/release-manifest.json != "
            "canonical/release-manifest.json — rebuild the wheel after the manifest edit"
        )
    notes.append(f"ok {wheel.name} release-manifest.json matches canonical")
    return notes


def check_pypi_cutover_readiness(*, live: bool = False) -> list[str]:
    """AUCT-028/036: preflight before flipping ``pypi_live=true``.

    Verifies Trusted Publishing workflow OIDC wiring, wheel packaging
    exclusions/inclusions, and prints the cutover order: claim, bump+flip PR,
    publish, live probe, tag. Does **not** flip ``pypi_live`` or publish.
    Optional ``live=True`` queries the public PyPI JSON API and raises unless
    the probe is HTTP 200. The packaged manifest must match canonical, and so
    must a built wheel for this version when ``tools/dist`` has one.
    """
    from auctelis.versioning import product_version

    root = repo_root()
    actions: list[str] = [_check_recruitment_cutover_order()]

    publish = root / ".github" / "workflows" / "publish-pypi.yml"
    if not publish.is_file():
        raise SystemExit("Missing .github/workflows/publish-pypi.yml")
    text = publish.read_text(encoding="utf-8")
    if "id-token: write" not in text:
        raise SystemExit("publish-pypi.yml missing OIDC id-token: write permission")
    if "environment: pypi" not in text:
        raise SystemExit("publish-pypi.yml missing environment: pypi")
    if "uv publish" not in text:
        raise SystemExit("publish-pypi.yml missing uv publish step")
    if "pypi.org/pypi/auctelis" not in text:
        raise SystemExit("publish-pypi.yml missing PyPI HTTP 200 assert")
    actions.append("ok publish-pypi.yml OIDC + uv publish + PyPI assert")

    wheel_notes = check_wheel_omits_research()
    actions.extend(wheel_notes)

    pyproject = (root / "tools" / "pyproject.toml").read_text(encoding="utf-8")
    if "auctelis.cli:main" not in pyproject:
        raise SystemExit("tools/pyproject.toml missing auctelis console script entry")
    actions.append("ok tools/pyproject.toml declares auctelis console script")

    if _pypi_live():
        actions.append("note: pypi_live is already true — cutover docs must lead with uvx auctelis")
    else:
        actions.append("note: pypi_live=false — cutover not flipped yet (expected)")

    if live:
        import urllib.error
        import urllib.request

        ver = product_version()
        url = f"https://pypi.org/pypi/auctelis/{ver}/json"
        status: int
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                status = int(getattr(resp, "status", 200) or 200)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
        except urllib.error.URLError as exc:
            raise SystemExit(f"PyPI live check failed for {url}: {exc}") from exc
        print(f"PyPI HTTP {status} for auctelis/{ver} ({url})")
        actions.append(f"ok live PyPI probe HTTP {status} for auctelis/{ver}")
        if status != 200:
            # Loud on any miss. A 404 while pypi_live is still false is expected
            # before the claim; --live is the post-publish probe, so it fails.
            prefix = "pypi_live=true but " if _pypi_live() else ""
            raise SystemExit(
                f"{prefix}PyPI live probe returned HTTP {status} for auctelis/{ver} (expected 200)"
            )

    actions.extend(_release_manifest_parity())

    checklist = [
        "",
        "PyPI cutover order (manual; do not automate the upload here):",
        "  1. Claim `auctelis` on PyPI and add a Trusted Publisher",
        "     (owner roham-amd / repo auctelis / workflow publish-pypi.yml / env pypi).",
        "  2. Bump+flip PR: set pypi_live=true in canonical/release-manifest.json,",
        '     AUCTELIS_PYPI_DEFAULT="true" in both action.yml copies (byte-identical),',
        "     and lead install docs with `uvx auctelis check`.",
        "  3. Publish that flipped commit with publish-pypi.yml (workflow_dispatch).",
        "  4. Live probe: poll https://pypi.org/pypi/auctelis/<ver>/json until HTTP 200",
        "     (≤10 min), then run `auctelis-dev build pypi-check --live`.",
        "  5. Tag the release only after the live probe is HTTP 200.",
        "",
    ]
    for line in checklist:
        print(line)
    return actions


def check_dogfood_lock_freshness() -> list[str]:
    """AUCT-033: fail ``build all`` when dogfood AUTHORITY.lock drifts.

    Catches representation / workflow / skill digest churn locally before a
    release tag is pushed (the failure mode that left ``v0.1.0`` with empty
    Release assets).
    """
    from auctelis.authority_lock import check_locked

    root = repo_root()
    lock_path = root / "AUTHORITY.lock"
    if not lock_path.is_file():
        raise SystemExit(
            "Missing AUTHORITY.lock at repo root — dogfood lock required for build all"
        )
    report, code = check_locked(root, lock_path=lock_path, strict_digests=True)
    if code != 0 or not report.get("ok"):
        lines = report.get("lines") or []
        detail = "\n".join(str(line) for line in lines[:12]) or str(
            report.get("error") or "authority changed"
        )
        raise SystemExit(
            "Dogfood AUTHORITY.lock is stale vs the tree (strict digests). "
            "Run `auctelis lock --update` and commit before tagging.\n"
            f"{detail}"
        )
    return ["ok dogfood AUTHORITY.lock matches tree (strict digests)"]


def build_all() -> dict[str, object]:
    sync = sync_schemas()
    packaged = sync_packaged_version_metadata()
    check_schema_parity()
    check_demo_fixture_parity()
    check_version_metadata()
    check_requires_python()
    action_parity = check_action_parity()
    dep_pins = check_dependency_pins()
    validate_json_schema_document()
    links = check_internal_markdown_links()
    wheel_lean = check_wheel_omits_research()
    dogfood_lock = check_dogfood_lock_freshness()
    return {
        "schemas": sync,
        "packaged_metadata": packaged,
        "dependency_pins": dep_pins,
        "action_parity": action_parity,
        "markdown_files_link_checked": links,
        "wheel_omits_research": wheel_lean,
        "dogfood_lock_freshness": dogfood_lock,
        # Monolith generation removed from product build (archive/methodology only).
        "status": "ok",
    }
