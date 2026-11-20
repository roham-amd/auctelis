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
_AGENT_RUN_RE = re.compile(
    r"(?:\bclaude\b|\bcursor\b|\bcodex\b|\baider\b|\bopenhands\b|"
    r"\bcopilot\b|\bgemini\b|"
    r"npx\s+(?:-[^\s]+\s+)*(?:-y\s+)?[^\s|]*agent|"
    r"npx\s+(?:-[^\s]+\s+)*(?:-y\s+)?@modelcontextprotocol|"
    r"npx\s+(?:-[^\s]+\s+)*(?:-y\s+)?@github/copilot|"
    r"pipx?\s+run\s+aider|uvx\s+aider)",
    re.IGNORECASE,
)
_EMPTY_PERMISSIONS_RE = re.compile(r"permissions:\s*\{\s*\}", re.MULTILINE)


def workflow_text_has_agent_step(raw: str) -> bool:
    """True when YAML lines show a real agent action or CLI — not bare name tokens."""
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lower = stripped.lower()
        if lower.startswith(("uses:", "- uses:")):
            if _AGENT_USE_RE.search(stripped):
                return True
            continue
        if "run:" in lower:
            run_part = stripped.split("run:", 1)[-1]
            if _AGENT_RUN_RE.search(run_part):
                return True
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
