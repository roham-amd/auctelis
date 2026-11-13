from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from auctelis.inventory.io import safe_read_text, select_files
from auctelis.inventory.limits import CollectorLimits

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Bare "token" / "password" match design-token docs and PDF passwords — require
# credential-shaped phrases instead.
_SECRET_TOKEN_RE = re.compile(
    r"\b("
    r"secrets?|api[_-]?key|apikey|passwd|"
    r"(?:api|access|auth|bearer|github|oauth|session|refresh)[_ -]?tokens?|"
    r"credentials?|1password|op_service_account|"
    r"(?:env|environment)[_ ](?:var(?:iable)?s?|secrets?)"
    r")\b",
    re.IGNORECASE,
)
_PASSWORD_CRED_RE = re.compile(
    r"\b(password|passwd)\b(?![^\n]{0,40}\b(pdf|document|zip|archive|file)\b)",
    re.IGNORECASE,
)
_NEGATION_RE = re.compile(
    r"\b(no|not|without|never|don't|do not|avoid|forbid(?:den)?|remove|removing)\b",
    re.IGNORECASE,
)
_HIDDEN_UNICODE_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069]")
_DOWNLOAD_EXEC_RE = re.compile(
    r"(curl\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"wget\s+[^\n|;]*\|\s*(?:sudo\s+)?(?:ba)?sh|"
    r"iwr\s+[^\n|;]*\|\s*iex|invoke-webrequest[^\n|;]*\|\s*iex)",
    re.IGNORECASE,
)
_PERMISSION_BYPASS_RE = re.compile(
    r"(--dangerously-skip-permissions|--yolo\b|bypasspermissions|"
    r"permissionmode\s*[:=]\s*bypass|auto[_-]?approve\s*[:=]\s*true|"
    r"skip[_-]?permissions)",
    re.IGNORECASE,
)
_INSTRUCTION_ABUSE_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "do not tell the user",
    "hide this action",
    "bypass confirmation",
    "skip approval",
    "exfiltrate",
    "fetch and execute",
    "download and run",
)
_HTML_COMMENT_RE = re.compile(r"<!--([\s\S]*?)-->")
_EXECUTABLE_EVIDENCE = {
    "bundled_scripts_directory",
    "possible_code_execution_reference",
    "download_and_execute",
    "script_reference",
}


def _mentions_secret_handling(text: str) -> bool:
    """True when credential-shaped tokens appear outside a short negation window."""
    for match in list(_SECRET_TOKEN_RE.finditer(text)) + list(_PASSWORD_CRED_RE.finditer(text)):
        start = max(0, match.start() - 48)
        window = text[start : match.start()]
        if _NEGATION_RE.search(window):
            continue
        return True
    return False


def _mentions_identity_workflow(text: str) -> bool:
    if "service_account" in text or "op signin" in text:
        start_idx = text.find("service_account")
        if start_idx < 0:
            start_idx = text.find("op signin")
        window = text[max(0, start_idx - 48) : start_idx]
        return not bool(_NEGATION_RE.search(window))
    return False


def _html_comment_instruction_abuse(raw: str) -> bool:
    for match in _HTML_COMMENT_RE.finditer(raw):
        body = match.group(1).lower()
        if any(marker in body for marker in _INSTRUCTION_ABUSE_MARKERS):
            return True
        if "ignore previous" in body or "system prompt" in body:
            return True
    return False


def discover_skills(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in select_files(files, lambda p: p.name == "SKILL.md"):
        raw = safe_read_text(path, root=root, limits=limits, events=events, adapter="skill_md")
        if raw is None:
            continue
        rel = path.relative_to(root)
        name = path.parent.name
        description = None
        fm = _FRONTMATTER_RE.match(raw)
        if fm:
            for line in fm.group(1).splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip('"')
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"')

        hints: list[str] = []
        lowered = raw.lower()
        if "http://" in lowered or "https://" in lowered:
            hints.append("external_url_reference")
        if any(token in lowered for token in ("subprocess", "os.system", "bash ", "powershell")):
            hints.append("possible_code_execution_reference")
        if any(
            token in lowered for token in (".sh", ".ps1", "```python", "```bash", "```powershell")
        ):
            hints.append("script_reference")
        if _mentions_secret_handling(lowered):
            hints.append("secrets_or_credential_handling")
        if _mentions_identity_workflow(lowered):
            hints.append("identity_or_auth_workflow")
        # Bundled helper scripts next to the skill raise authority questions.
        if any((path.parent / "scripts").glob("*")):
            hints.append("bundled_scripts_directory")
        if _HIDDEN_UNICODE_RE.search(raw):
            hints.append("hidden_unicode_in_instructions")
        if _DOWNLOAD_EXEC_RE.search(raw):
            hints.append("download_and_execute")
        if _PERMISSION_BYPASS_RE.search(raw):
            hints.append("permission_bypass_flag")
        if any(marker in lowered for marker in _INSTRUCTION_ABUSE_MARKERS):
            hints.append("instruction_abuse_content")
        if _html_comment_instruction_abuse(raw):
            hints.append("instruction_abuse_content")
            hints.append("hidden_html_comment_instructions")
        # Mark whether escalation to SECURITY_FINDING is justified.
        if set(hints).intersection(_EXECUTABLE_EVIDENCE):
            hints.append("executable_evidence")

        results.append(
            {
                "name": name,
                "type": "Skill",
                "reference_kind": "LOCAL_IMPLEMENTATION",
                "repository_path": str(rel).replace("\\", "/"),
                "adapter": "skill_md",
                "adapter_maturity": "SUPPORTED",
                "discovery_status": "IDENTIFIED",
                "instruction_content_present": True,
                "declared_description": description,
                "priority_hints": hints,
            }
        )
    return results
