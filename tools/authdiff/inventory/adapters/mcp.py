from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from authdiff.inventory.env_routing import is_routing_override_env_key
from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.jsonc import loads_json_tolerant
from authdiff.inventory.limits import CollectorLimits

_SECRETISH_ENV_RE = re.compile(
    r"(api[_-]?key|token|secret|password|passwd|authorization|credential|private[_-]?key)",
    re.IGNORECASE,
)
_DOWNLOAD_EXEC_RE = re.compile(
    r"(curl\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"wget\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"iwr\s+[^\n|;]*\|\s*iex|invoke-webrequest[^\n|;]*\|\s*iex)",
    re.IGNORECASE,
)


_FLOATING_TAGS = frozenset(
    {"latest", "next", "canary", "beta", "alpha", "rc", "dev", "main", "master", "trunk"}
)
_EXACT_SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_PLACEHOLDER_SECRET_RE = re.compile(
    r"(?i)^(your[-_]?|my[-_]?|example[-_]?|changeme|todo|fixme|xxx+|placeholder|"
    r"<[^>]+>|\[+[^\]]+\]+)$"
)
_KNOWN_TOKEN_FORMAT_RE = re.compile(
    r"^(ghp_|gho_|github_pat_|sk-|sk-ant-|xox[baprs]-|AKIA[0-9A-Z]{16}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
)


def _version_looks_exact(version: str) -> bool:
    ver = version.strip()
    if not ver or ver.lower() in _FLOATING_TAGS:
        return False
    if ver.startswith(("^", "~", "*", ">", "<")):
        return False
    if ver.endswith("*") or "x" in ver.lower().split(".")[-1:]:
        return False
    return bool(_EXACT_SEMVER_RE.match(ver))


def _package_looks_pinned(token: str) -> bool:
    """True only for exact semver or digest pins — not `@latest` / `@next` / git@.

    Scoped npm names (`@scope/pkg`) are not pins. `git@github.com:...` is not a pin.
    """
    if "@sha256:" in token or token.startswith("sha256:"):
        return True
    if "==" in token:
        # pip-style name==1.2.3
        _, _, ver = token.partition("==")
        return _version_looks_exact(ver)
    # Reject SSH git URLs that merely contain @.
    if token.startswith("git@") or "git@" in token:
        return False
    if token.startswith("@"):
        # @scope/name → unpinned; @scope/name@1.2.3 → maybe pinned
        if token.count("@") < 2:
            return False
        version = token.rsplit("@", 1)[-1]
        return _version_looks_exact(version)
    if "@" not in token:
        return False
    version = token.rsplit("@", 1)[-1]
    return _version_looks_exact(version)


def _looks_unpinned_launcher(command: str, args: list[Any]) -> bool:
    """True for npx/uvx/bunx/pipx/docker launchers without an exact pin."""
    cmd = command.strip().lower()
    arg_strs = [str(a) for a in args]
    joined = " ".join(arg_strs)
    if cmd in {"npx", "bunx"} and ("-y" in arg_strs or "--yes" in arg_strs):
        pkgs = [a for a in arg_strs if a not in {"-y", "--yes", "--"} and not a.startswith("-")]
        return bool(pkgs) and not any(_package_looks_pinned(p) for p in pkgs)
    if cmd in {"uvx", "pipx"}:
        return bool(arg_strs) and not any(_package_looks_pinned(a) for a in arg_strs)
    if cmd in {"docker", "podman"}:
        # docker run image:tag — :latest or bare name is floating
        images = [a for a in arg_strs if not a.startswith("-") and a not in {"run", "exec"}]
        for image in images:
            if ":" not in image:
                return True
            tag = image.rsplit(":", 1)[-1]
            if tag.lower() in _FLOATING_TAGS or tag.lower() == "latest":
                return True
            if "@sha256:" in image:
                return False
        return False
    if "npx -y" in f"{cmd} {joined}" or "npx --yes" in f"{cmd} {joined}":
        return not any(_package_looks_pinned(a) for a in arg_strs)
    return False


def _env_secret_severity_hint(env: Any) -> str | None:
    """Return hint name for literal secrets: critical format vs medium placeholder-ish."""
    if not isinstance(env, dict):
        return None
    saw_medium = False
    for key, value in env.items():
        key_s = str(key)
        val_s = str(value) if value is not None else ""
        if not _SECRETISH_ENV_RE.search(key_s):
            continue
        # Placeholder / env expansion is inheritance (RULE-002), not a literal secret.
        if val_s.startswith("${") or val_s.startswith("$(") or val_s.startswith("{{"):
            continue
        if val_s.startswith("$"):
            continue
        if len(val_s) < 8:
            continue
        if _PLACEHOLDER_SECRET_RE.match(val_s.strip()) or val_s.strip().lower() in {
            "your-api-key-here",
            "replace-me",
            "insert-token",
            "redacted",
        }:
            saw_medium = True
            continue
        if _KNOWN_TOKEN_FORMAT_RE.match(val_s.strip()) or _entropy_high(val_s):
            return "literal_secret_in_env"
        saw_medium = True
    if saw_medium:
        return "literal_secret_like_placeholder"
    return None


def _entropy_high(value: str) -> bool:
    """Rough printable entropy gate — avoids flagging `password1` as CRITICAL."""
    if len(value) < 16:
        return False
    unique = len(set(value))
    return unique >= max(10, len(value) // 4)


def _env_passes_host_secrets(env: Any) -> bool:
    """True when env keys look credential-shaped and values are host expansions."""
    if not isinstance(env, dict):
        return False
    for key, value in env.items():
        if not _SECRETISH_ENV_RE.search(str(key)):
            continue
        val_s = str(value) if value is not None else ""
        if (
            val_s.startswith("${")
            or val_s.startswith("$(")
            or (val_s.startswith("$") and not val_s.startswith("$$"))
        ):
            return True
    return False


def _is_broad_path_arg(arg: Any) -> bool:
    """True only for root / home / parent-traversal roots — not project abs paths."""
    s = str(arg).strip()
    if not s:
        return False
    lowered = s.lower()
    if lowered in {"/", "~", "$home", "${home}", "%userprofile%", "%homepath%"}:
        return True
    if s.startswith("~/") or s.startswith("~\\"):
        return True
    if s in {".."} or s.startswith("../") or s.startswith("..\\"):
        return True
    # Windows drive root: C:\ or C:/
    if re.fullmatch(r"[A-Za-z]:[\\/]?", s):
        return True
    try:
        parts = Path(s).parts
    except (TypeError, ValueError):
        return False
    return ".." in parts


_KNOWN_MCP_REL_PATHS = frozenset(
    {
        ".cursor/mcp.json",
        ".vscode/mcp.json",
        ".gemini/settings.json",
        ".zed/settings.json",
        ".zed/settings.local.json",
        ".config/zed/settings.json",
        ".continue/config.json",
        ".codex/mcp.json",
        ".kiro/settings/mcp.json",
        ".kiro/mcp.json",
        ".roo/mcp.json",
        ".amazonq/mcp.json",
        ".opencode/mcp.json",
        ".opencode/settings.json",
        "opencode.json",
    }
)


def _coerce_server_map(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items() if isinstance(v, dict)}
    if isinstance(raw, list):
        out: dict[str, Any] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("id") or item.get("server")
            if name:
                out[str(name)] = item
        return out
    return {}


def _extract_mcp_servers(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("mcpServers", "servers", "context_servers", "mcp_servers"):
        block = data.get(key)
        if block:
            servers = _coerce_server_map(block)
            if servers:
                return servers
    mcp = data.get("mcp")
    if isinstance(mcp, dict):
        for key in ("servers", "mcpServers"):
            block = mcp.get(key)
            if block:
                servers = _coerce_server_map(block)
                if servers:
                    return servers
    exp = data.get("experimental")
    if isinstance(exp, dict):
        for key in ("modelContextProtocolServers", "mcpServers"):
            block = exp.get(key)
            if block:
                servers = _coerce_server_map(block)
                if servers:
                    return servers
    return {}


def _host_id_from_repository_path(rel: str) -> str:
    lowered = rel.lower()
    padded = f"/{lowered}"
    for marker, hid in (
        (".cursor/", "cursor"),
        (".claude/", "claude-code"),
        (".vscode/", "vscode"),
        (".codex/", "codex"),
        (".gemini/", "gemini"),
        (".windsurf/", "windsurf"),
        (".zed/", "zed"),
        (".config/zed/", "zed"),
        (".continue/", "continue"),
        (".kiro/", "kiro"),
        (".roo/", "roo-code"),
        (".amazonq/", "amazon-q"),
        (".opencode/", "opencode"),
    ):
        if marker in padded:
            return hid
    if lowered in {"opencode.json", ".claude.json", ".mcp.json"}:
        if "opencode" in lowered:
            return "opencode"
        return "claude-code"
    return ""


def _is_mcp_config_candidate(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    if name in {
        "mcp.json",
        "mcp_config.json",
        "mcp_example.json",
        ".mcp.json",
        ".claude.json",  # Claude Code user-scope MCP registry
    }:
        return True
    if name.endswith(".json") and "mcp" in name:
        return True
    return rel in _KNOWN_MCP_REL_PATHS


def _is_mcp_server_source(path: Path) -> bool:
    name = path.name.lower()
    if not name.endswith((".py", ".ts", ".js", ".mjs")):
        return False
    if "mcp" in name:
        return True
    parts = {p.lower() for p in path.parts}
    return "mcp" in parts and name.endswith((".py", ".ts", ".js", ".mjs"))


def discover_mcp_configs(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in select_files(files, lambda p: _is_mcp_config_candidate(p, root)):
        key = path.resolve()
        if key in seen:
            continue
        seen.add(key)
        raw = safe_read_text(path, root=root, limits=limits, events=events, adapter="mcp_config")
        rel = path.relative_to(root).as_posix()
        if raw is None:
            # Oversize / unreadable agent config — fail closed via coverage events.
            events.append(
                {
                    "type": "unparsed_agent_config",
                    "adapter": "mcp_config",
                    "path": rel,
                    "message": "MCP config could not be read (oversize, truncated, or I/O error)",
                }
            )
            continue
        try:
            data = loads_json_tolerant(raw)
        except json.JSONDecodeError as exc:
            events.append(
                {
                    "type": "parse_error",
                    "adapter": "mcp_config",
                    "path": rel,
                    "message": str(exc),
                    "agent_config": True,
                }
            )
            events.append(
                {
                    "type": "unparsed_agent_config",
                    "adapter": "mcp_config",
                    "path": rel,
                    "message": str(exc),
                }
            )
            continue

        if not isinstance(data, dict):
            continue
        servers = _extract_mcp_servers(data)
        if not servers:
            # Candidate filename but not an MCP registration document.
            continue

        example_like = "example" in path.name.lower()
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            hints: list[str] = []
            if example_like:
                hints.append("example_or_template_config")
            command = str(cfg.get("command") or "")
            raw_args = cfg.get("args")
            args: list[Any] = list(raw_args) if isinstance(raw_args, list) else []
            if command:
                hints.append("local_command_transport")
                if _looks_unpinned_launcher(command, args):
                    hints.append("unpinned_package_launcher")
            env = cfg.get("env") or cfg.get("environment")
            if env:
                hints.append("sets_environment")
                secret_hint = _env_secret_severity_hint(env)
                if secret_hint:
                    hints.append(secret_hint)
                elif _env_passes_host_secrets(env):
                    # Only credential-shaped keys with host expansion escalate RULE-002.
                    hints.append("inherits_or_sets_environment")
            url = str(cfg.get("url") or "")
            if url:
                hints.append("remote_endpoint")
                if url.lower().startswith("http://"):
                    hints.append("insecure_http_remote")
            if isinstance(args, list) and any(_is_broad_path_arg(a) for a in args):
                hints.append("broad_or_relative_path_args")
            joined_cmd = f"{command} {' '.join(str(a) for a in args)}"
            if _DOWNLOAD_EXEC_RE.search(joined_cmd):
                hints.append("download_and_execute")
            if any(
                token in joined_cmd.lower()
                for token in (
                    "dangerously-skip-permissions",
                    "bypasspermissions",
                    "--yolo",
                    "skip-permissions",
                )
            ):
                hints.append("permission_bypass_flag")
            env_keys: list[str] = []
            url_destinations: list[str] = []
            mcp_detail: dict[str, Any] = {}
            if isinstance(env, dict):
                env_keys = sorted(str(k) for k in env)
                for ek, ev in env.items():
                    if not is_routing_override_env_key(ek):
                        continue
                    hints.append("base_url_or_proxy_override")
                    if not mcp_detail.get("override_key"):
                        mcp_detail["override_key"] = str(ek)
                    val = str(ev or "").strip()
                    if val and not val.startswith("${"):
                        url_destinations.append(val)
            elif isinstance(env, list):
                env_keys = sorted(str(item) for item in env if isinstance(item, str))
            # Derive a coarse host id from path so copying the same server under
            # another host tree is a distinct authority record.
            host_id = _host_id_from_repository_path(rel)
            entry: dict[str, Any] = {
                "name": name,
                "type": "MCP Server Registration",
                "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                "repository_path": rel,
                "adapter": "mcp_config",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "declared_transport": cfg.get("transport") or cfg.get("type"),
                "command": cfg.get("command"),
                "args": list(args) if isinstance(args, list) else [],
                "url": cfg.get("url"),
                "env_keys": env_keys,
                "host_id": host_id,
                "priority_hints": hints,
            }
            if url_destinations:
                entry["destinations"] = sorted(set(url_destinations))
            if mcp_detail:
                entry["mcp_detail"] = mcp_detail
            results.append(entry)

    # MCP server implementations (source), distinct from client registration JSON.
    for path in select_files(files, _is_mcp_server_source):
        raw = safe_read_text(
            path, root=root, limits=limits, events=events, adapter="mcp_server_source"
        )
        if raw is None:
            continue
        lowered = raw.lower()
        name_has_mcp = "mcp" in path.name.lower()
        has_protocol_marker = any(
            token in lowered
            for token in ("fastmcp", "mcp.server", "@modelcontextprotocol", "mcp = ")
        )
        if not name_has_mcp and not has_protocol_marker:
            continue

        rel = path.relative_to(root).as_posix()
        server_hints: list[str] = ["mcp_server_source"]
        if "urllib" in lowered or "requests." in lowered or "httpx" in lowered:
            server_hints.append("network_client_in_server")
        if "write_bytes" in lowered or ("open(" in lowered and '"w' in lowered):
            server_hints.append("filesystem_write_capability_reference")
        if "subprocess" in lowered or "os.system" in lowered:
            server_hints.append("possible_code_execution_reference")
        if "github.com" in lowered or "api.github.com" in lowered:
            server_hints.append("github_fetch_capability")

        results.append(
            {
                "name": path.stem,
                "type": "MCP Server Implementation",
                "reference_kind": "LOCAL_IMPLEMENTATION",
                "repository_path": rel,
                "adapter": "mcp_server_source",
                "adapter_maturity": "PARTIAL",
                "discovery_status": "IDENTIFIED",
                "priority_hints": server_hints,
            }
        )

    return results
