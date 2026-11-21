"""Shared heuristics for CI workflow authority signals (Week 3 calibration)."""

from __future__ import annotations

import re

_AGENT_USE_RE = re.compile(
    r"uses:\s*\S*(?:"
    r"anthropic|claude|cursoragent|openai|codex|modelcontextprotocol|/agent[-/]|"
    r"github/copilot|copilot-coding-agent|google-github-actions/run-gemini-cli|"
    r"gemini-cli|all-hands-ai/openhands|openhands|"
    r"paulfchristiano/aider|aider-ai/aider"
    r")",
    re.IGNORECASE,
)

# Bare product names only match in command-invocation position (AUCT-029):
# start of the run: value, or after && || ; |, with optional KEY=VAL env prefixes.
# Never match inside arguments/strings (e.g. pytest -k cursor, echo gemini).
_AGENT_BARE_NAMES = r"(?:claude|cursor|codex|aider|openhands|copilot|gemini)"
_ENV_PREFIX = r"(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*"
_CMD_BOUNDARY = rf"(?:^|&&|\|\||;|\|)\s*{_ENV_PREFIX}"
_AGENT_BARE_CMD_RE = re.compile(
    rf"{_CMD_BOUNDARY}{_AGENT_BARE_NAMES}\b",
    re.IGNORECASE,
)
# Package-runner agent CLIs (npx/uvx/pipx) — package path is the signal.
_AGENT_RUN_TOOL_RE = re.compile(
    r"(?:"
    r"npx\s+(?:-[^\s]+\s+)*(?:-y\s+)?[^\s|]*agent|"
    r"npx\s+(?:-[^\s]+\s+)*(?:-y\s+)?@modelcontextprotocol|"
    r"npx\s+(?:-[^\s]+\s+)*(?:-y\s+)?@github/copilot|"
    r"pipx?\s+run\s+aider|uvx\s+aider|"
    # Bare name after a package runner still counts as invocation.
    rf"(?:npx|uvx|pipx)\s+(?:-[^\s]+\s+)*{_ENV_PREFIX}{_AGENT_BARE_NAMES}\b"
    r")",
    re.IGNORECASE,
)
_EMPTY_PERMISSIONS_RE = re.compile(r"permissions:\s*\{\s*\}", re.MULTILINE)
# GitHub Actions block scalars: run: | / |- / |+ / > / >- / >+
_RUN_BLOCK_SCALAR_RE = re.compile(
    r"^(\s*)(?:-\s*)?run:\s*([|>][+-]?)\s*(?:#.*)?$",
    re.IGNORECASE,
)
_RUN_INLINE_RE = re.compile(
    r"^(\s*)(?:-\s*)?run:\s*(.+)$",
    re.IGNORECASE,
)


def _line_has_agent_command(text: str) -> bool:
    return bool(_AGENT_BARE_CMD_RE.search(text) or _AGENT_RUN_TOOL_RE.search(text))


def workflow_text_has_agent_step(raw: str) -> bool:
    """True when YAML lines show a real agent action or CLI — not bare name tokens.

    AUCT-030: also scans multi-line ``run: |`` / ``run: >`` block-scalar bodies.
    """
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        lower = stripped.lower()
        if lower.startswith(("uses:", "- uses:")):
            if _AGENT_USE_RE.search(stripped):
                return True
            index += 1
            continue

        block = _RUN_BLOCK_SCALAR_RE.match(line)
        if block:
            key_indent = len(block.group(1).expandtabs(2))
            index += 1
            while index < len(lines):
                body = lines[index]
                body_stripped = body.strip()
                if not body_stripped:
                    index += 1
                    continue
                # Expand tabs before comparing indent to the `run:` key column.
                leading = body[: len(body) - len(body.lstrip(" \t"))]
                body_indent = len(leading.expandtabs(2))
                if body_indent <= key_indent:
                    break
                if body_stripped.startswith("#"):
                    index += 1
                    continue
                if _line_has_agent_command(body_stripped):
                    return True
                index += 1
            continue

        inline = _RUN_INLINE_RE.match(line)
        if inline:
            run_part = inline.group(2).strip()
            # Ignore a bare block-scalar marker already handled above.
            if (
                run_part
                and not re.fullmatch(r"[|>][+-]?(?:\s+#.*)?", run_part)
                and _line_has_agent_command(run_part)
            ):
                return True
            index += 1
            continue

        # Legacy fallback: "run:" anywhere on the line (folded keys / odd YAML).
        if "run:" in lower:
            run_part = stripped.split("run:", 1)[-1].strip()
            if run_part and _line_has_agent_command(run_part):
                return True
        index += 1
    return False


def workflow_mitigation_hints(raw: str) -> list[str]:
    hints: list[str] = []
    lowered = raw.lower()
    if _EMPTY_PERMISSIONS_RE.search(raw):
        hints.append("explicit_empty_permissions")
    if re.search(r"permissions:\s*read-all", lowered):
        hints.append("minimal_github_permissions")
    if "types:" in lowered and "labeled" in lowered:
        hints.append("label_only_trigger")
    if any(
        tok in lowered for tok in ("github.actor", "github.repository_owner", "head.repo.full_name")
    ):
        hints.append("actor_or_same_repo_guard")
    return hints


def analyze_github_workflow(raw: str) -> list[str]:
    """Return priority_hints for a GitHub Actions workflow file."""
    hints: list[str] = []
    lowered = raw.lower()
    if "permissions:" in lowered:
        hints.append("explicit_github_permissions_block")
    if "secrets." in lowered or "${{ secrets" in lowered:
        hints.append("secret_reference")
    if "pull_request_target" in lowered:
        hints.append("pull_request_target")
    if "workflow_dispatch" in lowered:
        hints.append("manual_dispatch")
    if any(tok in lowered for tok in ("curl ", "wget ", "pip install", "npm install")):
        hints.append("install_or_network_step_reference")

    mitigations = workflow_mitigation_hints(raw)
    if mitigations:
        hints.append("workflow_mitigation_present")
        hints.extend(mitigations)

    if workflow_text_has_agent_step(raw):
        hints.append("agent_related_step")

    if (
        "pull_request_target" in hints
        and "agent_related_step" in hints
        and "workflow_mitigation_present" not in hints
    ):
        hints.append("pull_request_target_with_agent")

    return hints
