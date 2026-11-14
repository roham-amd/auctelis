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
from auctelis.pins import normalize_package_name
from auctelis.supply_chain.digest import sha256_file
from auctelis.versioning import load_versions as load_canonical_versions


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
    packaged_version = data_dir / "VERSION"
    if packaged_version.read_text(encoding="utf-8") != product:
        packaged_version.write_text(product, encoding="utf-8")
        actions.append("updated tools/auctelis/data/VERSION")
    else:
        actions.append("unchanged tools/auctelis/data/VERSION")

    for name in ("versions.json", "release-manifest.json"):
        src = root / "canonical" / name
        dest = data_dir / name
        if not src.is_file():
            raise SystemExit(f"Missing canonical/{name}")
        src_text = src.read_text(encoding="utf-8")
        if not dest.is_file() or dest.read_text(encoding="utf-8") != src_text:
            dest.write_text(src_text, encoding="utf-8")
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
    check_bare_command_docs()
    check_policy_schema_contract()


def check_install_doc_versions(product: str) -> None:
    """INSTALL.md version table must match root VERSION / package version."""
    install = repo_root() / "docs" / "INSTALL.md"
    text = install.read_text(encoding="utf-8")
    for label in ("Product (`VERSION`)", "Package `auctelis`"):
        match = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([^\s|]+)\s*\|", text)
        if not match:
            raise SystemExit(f"docs/INSTALL.md missing version row for {label}")
        if match.group(1) != product:
            raise SystemExit(f"docs/INSTALL.md {label} is {match.group(1)!r}, expected {product!r}")


def check_bare_command_docs() -> None:
    """Public docs must describe doctor-or-scan bare CLI, not scan-only."""
    root = repo_root()
    stale = re.compile(
        r"bare\s+`auctelis`[^.?\n]{0,80}defaults to\s+`?(?:auctelis\s+)?scan",
        re.IGNORECASE,
    )
    for rel in (
        "docs/INSTALL.md",
        "docs/CLI-REFERENCE.md",
        "docs/GUARD-SCAN.md",
        "docs/AUCTELIS-GATE.md",
        "tools/README.md",
    ):
        path = root / rel
        text = path.read_text(encoding="utf-8")
        if stale.search(text):
            raise SystemExit(
                f"{rel} still claims bare auctelis defaults only to scan; "
                "document doctor (no lock/policy) or scan . (when present)"
            )


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


def validate_examples() -> list[str]:
    root = repo_root()
    schema = json.loads(canonical_schema_path().read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    results: list[str] = []
    for example in sorted((root / "examples").glob("*.json")):
        doc = json.loads(example.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
        if errors:
            msgs = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
            raise SystemExit(f"Example failed schema validation: {example.name}: {msgs}")
        results.append(f"ok {example.name}")
    return results


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
    }
)


def _skip_markdown_path(path: Path) -> bool:
    if _SKIP_MD_PARTS.intersection(path.parts):
        return True
    return any(part == "auctelis-out" or part.startswith("auctelis-out-") for part in path.parts)


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
    from auctelis.deps import ensure_lock_in_sync, parse_declared_requirements, parse_lock_pins

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


def build_all() -> dict[str, object]:
    sync = sync_schemas()
    packaged = sync_packaged_version_metadata()
    check_schema_parity()
    check_demo_fixture_parity()
    check_version_metadata()
    check_requires_python()
    dep_pins = check_dependency_pins()
    validate_json_schema_document()
    examples = validate_examples()
    links = check_internal_markdown_links()
    return {
        "schemas": sync,
        "packaged_metadata": packaged,
        "examples": examples,
        "dependency_pins": dep_pins,
        "markdown_files_link_checked": links,
        # Monolith generation removed from product build (archive/methodology only).
        "status": "ok",
    }
