"""Repository-level authdiff policy (``.authdiff.yml``).

Declarative defaults for fail-on, baselines, output directory, and suppressions.
CLI flags always override file values when explicitly provided.

Uses a deterministic indent-based YAML subset parser (no PyYAML dependency) so
CI and developer environments behave identically.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

_RULE_ID_RE = re.compile(r"^AUTHDIFF-RULE-\d{3}$")


@dataclass
class Suppression:
    rule: str
    path: str = "**"
    justification: str = ""
    owner: str = ""
    expires: str | None = None

    def is_expired(self, *, today: date | None = None) -> bool:
        if not self.expires:
            return False
        try:
            expiry = date.fromisoformat(self.expires[:10])
        except ValueError:
            return False
        return (today or date.today()) > expiry


@dataclass
class AuthdiffPolicy:
    """Repository policy loaded from ``.authdiff.yml``."""

    version: int = 1
    mode: str = "advisory"  # advisory | enforce
    fail_on: str = "never"  # never | high | any
    output_dir: Path | None = None
    baseline: Path | None = None
    require_review: list[str] = field(default_factory=list)
    suppressions: list[Suppression] = field(default_factory=list)
    source_path: Path | None = None

    def applies_to_finding(
        self,
        *,
        rule_id: str,
        evidence_paths: list[str],
        today: date | None = None,
    ) -> Suppression | None:
        for item in self.suppressions:
            if item.rule != rule_id or item.is_expired(today=today):
                continue
            patterns = item.path.replace("\\", "/")
            if patterns in {"**", "*", "", "**/*"}:
                return item
            if not evidence_paths:
                continue
            for path in evidence_paths:
                normalized = path.replace("\\", "/")
                # Support both basename globs and recursive ** patterns.
                if fnmatch.fnmatch(normalized, patterns) or fnmatch.fnmatch(
                    Path(normalized).name, patterns
                ):
                    return item
                if "**" in patterns:
                    suffix = patterns.split("**/", 1)[-1]
                    if suffix and fnmatch.fnmatch(normalized, f"*/{suffix}"):
                        return item
                    if suffix and fnmatch.fnmatch(normalized, suffix):
                        return item
        return None


# Backward-compatible alias (pre-rebrand name).
AesaPolicy = AuthdiffPolicy


def discover_policy_file(start: Path, *, stop_at: Path | None = None) -> Path | None:
    """Find ``.authdiff.yml`` within the scan tree only.

    Walks from ``start`` upward, but never above ``stop_at`` (default: the
    resolved start directory). This prevents silently loading an unrelated
    parent-directory policy outside the assessed repository.
    """
    current = start.resolve()
    if current.is_file():
        current = current.parent
    ceiling = (stop_at or current).resolve()
    if ceiling.is_file():
        ceiling = ceiling.parent
    while True:
        candidate = current / ".authdiff.yml"
        if candidate.is_file():
            return candidate
        if current == ceiling or current.parent == current:
            return None
        try:
            current.relative_to(ceiling)
        except ValueError:
            return None
        current = current.parent


def _as_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _parse_suppressions(raw: Any) -> list[Suppression]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("policy.ignore must be a list")
    out: list[Suppression] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"policy.ignore[{idx}] must be a mapping")
        rule = str(item.get("rule") or "").strip()
        if not _RULE_ID_RE.match(rule):
            raise ValueError(f"policy.ignore[{idx}].rule must look like AUTHDIFF-RULE-00N")
        justification = str(item.get("justification") or "").strip()
        if not justification:
            raise ValueError(f"policy.ignore[{idx}] requires justification")
        owner = str(item.get("owner") or "").strip()
        if not owner:
            raise ValueError(
                f"policy.ignore[{idx}] requires owner (accountable human for the suppression)"
            )
        expires = str(item["expires"]) if item.get("expires") is not None else None
        if expires:
            try:
                date.fromisoformat(expires[:10])
            except ValueError as exc:
                raise ValueError(f"policy.ignore[{idx}].expires must be YYYY-MM-DD") from exc
        else:
            raise ValueError(
                f"policy.ignore[{idx}] requires expires (YYYY-MM-DD) — suppressions must not be forever"
            )
        out.append(
            Suppression(
                rule=rule,
                path=str(item.get("path") or "**"),
                justification=justification,
                owner=owner,
                expires=expires,
            )
        )
    return out


def load_policy(path: Path) -> AuthdiffPolicy:
    """Load and validate a ``.authdiff.yml`` policy file."""
    data = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    version = int(data.get("version") or 1)
    if version != 1:
        raise ValueError(f"Unsupported .authdiff.yml version: {version}")
    policy_block = _as_mapping(data.get("policy"), label="policy")
    mode = str(policy_block.get("mode") or "advisory").lower()
    if mode not in {"advisory", "enforce"}:
        raise ValueError("policy.mode must be advisory or enforce")
    fail_on = str(policy_block.get("fail_on") or "never").lower()
    if fail_on not in {"never", "high", "any"}:
        raise ValueError("policy.fail_on must be never, high, or any")
    if mode == "enforce" and fail_on == "never":
        fail_on = "high"
    output_raw = policy_block.get("output_dir")
    baseline_raw = policy_block.get("baseline")
    require_review = policy_block.get("require_review") or []
    if not isinstance(require_review, list):
        raise ValueError("policy.require_review must be a list")
    base = path.parent
    return AuthdiffPolicy(
        version=version,
        mode=mode,
        fail_on=fail_on,
        output_dir=(base / str(output_raw)).resolve() if output_raw else None,
        baseline=(base / str(baseline_raw)).resolve() if baseline_raw else None,
        require_review=[str(x) for x in require_review],
        suppressions=_parse_suppressions(policy_block.get("ignore")),
        source_path=path.resolve(),
    )


def apply_policy_defaults(
    *,
    policy: AuthdiffPolicy | None,
    fail_on: str | None,
    fail_on_from_cli: bool,
) -> str | None:
    """Prefer explicit CLI ``--fail-on``; otherwise use policy file."""
    if fail_on_from_cli or policy is None:
        return None if fail_on in {None, "never"} else fail_on
    return None if policy.fail_on == "never" else policy.fail_on


def _strip_yaml_comment(line: str) -> str:
    """Drop unquoted ``# …`` trailers so ``fail_on: never  # note`` stays valid."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line


def _parse_flow_sequence(token: str) -> list[Any] | None:
    """Parse a single-line flow sequence ``[]`` / ``[a, b]``; else return None."""
    text = token.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return None
    inner = text[1:-1].strip()
    if not inner:
        return []
    items: list[Any] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    for ch in inner:
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
        elif ch == "," and not in_single and not in_double:
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf or inner.endswith(","):
        items.append("".join(buf).strip())
    return items


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Indent-aware subset: mappings, lists of mappings/scalars, quoted strings, flow ``[]``."""

    def parse_scalar(token: str) -> Any:
        if token in {"", "~", "null", "Null", "NULL"}:
            return None
        if token in {"true", "True", "TRUE"}:
            return True
        if token in {"false", "False", "FALSE"}:
            return False
        flow = _parse_flow_sequence(token)
        if flow is not None:
            return [parse_scalar(item) if item else None for item in flow]
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
            return token[1:-1]
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        return token

    entries: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = _strip_yaml_comment(raw)
        if not stripped.strip() or stripped.lstrip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        entries.append((indent, stripped.strip()))

    def next_child_kind(from_idx: int, parent_indent: int) -> str:
        for j in range(from_idx + 1, len(entries)):
            ind, cont = entries[j]
            if ind <= parent_indent:
                return "empty"
            return "list" if cont.startswith("- ") else "map"
        return "empty"

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for i, (indent, content) in enumerate(entries):
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unexpected list item: {content}")
            body = content[2:].strip()
            if ":" in body:
                key, _, rest = body.partition(":")
                item = {key.strip(): parse_scalar(rest.strip())}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(parse_scalar(body))
            continue

        if ":" not in content:
            raise ValueError(f"Invalid policy line: {content}")
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()

        if isinstance(parent, dict) and len(stack) > 1 and isinstance(stack[-2][1], list) and rest:
            parent[key] = parse_scalar(rest)
            continue

        if not isinstance(parent, dict):
            raise ValueError(f"Cannot assign '{key}' under a non-mapping")

        if rest:
            parent[key] = parse_scalar(rest)
            continue

        kind = next_child_kind(i, indent)
        if kind == "list":
            child_list: list[Any] = []
            parent[key] = child_list
            stack.append((indent, child_list))
        else:
            child_map: dict[str, Any] = {}
            parent[key] = child_map
            stack.append((indent, child_map))

    return root
