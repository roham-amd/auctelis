"""Host Authority Registry loader.

Profiles describe *where* host configuration usually lives and which permission
claims are **declared** in files versus **effective** only after host runtime
verification. Effective permissions are never inferred from profile presence alone.

Source of truth: ``authdiff/data/hosts/registry.json`` (packaged). Embedded
``_FALLBACK_PROFILES`` keep doctor usable if the data file is missing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

SupportLevel = Literal["SUPPORTED", "PARTIAL", "MANUAL_ONLY", "UNSUPPORTED"]
PermissionKind = Literal["declared", "effective"]


@dataclass(frozen=True, slots=True)
class HostConfigSurface:
    path_glob: str
    description: str
    permission_kind: PermissionKind
    notes: str = ""


@dataclass(frozen=True, slots=True)
class HostProfile:
    host_id: str
    display_name: str
    support: SupportLevel
    config_surfaces: tuple[HostConfigSurface, ...]
    declared_permission_fields: tuple[str, ...]
    effective_permission_requires: tuple[str, ...]
    limitations: tuple[str, ...] = field(default_factory=tuple)
    approval_models: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["config_surfaces"] = [asdict(s) for s in self.config_surfaces]
        return data


def _surface_from_dict(raw: dict[str, Any]) -> HostConfigSurface:
    notes = str(raw.get("notes") or "")
    keys = raw.get("authority_keys") or []
    if keys and not notes:
        notes = "authority_keys: " + ", ".join(str(k) for k in keys)
    kind = str(raw.get("permission_kind") or "declared")
    if kind not in {"declared", "effective"}:
        kind = "declared"
    return HostConfigSurface(
        path_glob=str(raw.get("path_glob") or ""),
        description=str(raw.get("description") or ""),
        permission_kind=cast(PermissionKind, kind),
        notes=notes,
    )


def _profile_from_dict(host_id: str, raw: dict[str, Any]) -> HostProfile:
    surfaces = tuple(
        _surface_from_dict(s) for s in (raw.get("config_surfaces") or []) if isinstance(s, dict)
    )
    support = str(raw.get("support") or "MANUAL_ONLY")
    if support not in {"SUPPORTED", "PARTIAL", "MANUAL_ONLY", "UNSUPPORTED"}:
        support = "MANUAL_ONLY"
    return HostProfile(
        host_id=host_id,
        display_name=str(raw.get("display_name") or host_id),
        support=cast(SupportLevel, support),
        config_surfaces=surfaces,
        declared_permission_fields=tuple(
            str(x) for x in (raw.get("declared_permission_fields") or [])
        ),
        effective_permission_requires=tuple(
            str(x) for x in (raw.get("effective_permission_requires") or [])
        ),
        limitations=tuple(str(x) for x in (raw.get("limitations") or [])),
        approval_models=tuple(str(x) for x in (raw.get("approval_models") or [])),
    )


def _registry_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "hosts" / "registry.json"


@lru_cache(maxsize=1)
def _load_registry_profiles() -> dict[str, HostProfile]:
    path = _registry_path()
    if not path.is_file():
        return dict(_FALLBACK_PROFILES)
    data = json.loads(path.read_text(encoding="utf-8"))
    hosts = data.get("hosts") or {}
    out: dict[str, HostProfile] = {}
    if isinstance(hosts, dict):
        for host_id, raw in hosts.items():
            if isinstance(raw, dict):
                out[str(host_id)] = _profile_from_dict(str(host_id), raw)
    return out or dict(_FALLBACK_PROFILES)


# Minimal embedded fallback if packaged registry is absent (installed-wheel edge case).
_FALLBACK_PROFILES: dict[str, HostProfile] = {
    "cursor": HostProfile(
        host_id="cursor",
        display_name="Cursor",
        support="PARTIAL",
        config_surfaces=(
            HostConfigSurface(".cursor/mcp.json", "MCP server registrations", "declared"),
            HostConfigSurface("skills/**/SKILL.md", "Skill packs", "declared"),
        ),
        declared_permission_fields=("mcpServers.*.command", "mcpServers.*.url"),
        effective_permission_requires=("Host approval mode (NOT VERIFIED from files alone)",),
        limitations=("Repository files declare intent only.",),
        approval_models=("per-call", "persistent-by-name"),
    ),
    "claude-code": HostProfile(
        host_id="claude-code",
        display_name="Claude Code",
        support="PARTIAL",
        config_surfaces=(
            HostConfigSurface(".claude/**", "Claude Code project configuration", "declared"),
            HostConfigSurface(".mcp.json", "MCP registrations", "declared"),
        ),
        declared_permission_fields=("hooks", "enableAllProjectMcpServers"),
        effective_permission_requires=("Runtime permission mode (NOT VERIFIED)",),
        limitations=("Declared settings are SOURCE_STATIC evidence only.",),
        approval_models=("per-call", "bypass"),
    ),
}


HOST_PROFILES: dict[str, HostProfile] = dict(_load_registry_profiles())


def list_host_profiles() -> list[dict[str, Any]]:
    return [p.to_dict() for p in HOST_PROFILES.values()]


def get_host_profile(host_id: str) -> HostProfile | None:
    return HOST_PROFILES.get(host_id)
