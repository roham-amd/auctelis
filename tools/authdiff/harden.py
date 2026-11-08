"""Least-privilege patch suggestions (`authdiff harden`).

Dry-run only in this release. Emits config diffs for high-confidence
LITERAL_CONFIG / INFERRED_HINT gated rules. Never edits the target tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from authdiff.jsonio import read_json
from authdiff.security.gating import is_gate_finding

# Rule → minimal remediation template (review required; may break working setups).
_PATCH_TEMPLATES: dict[str, dict[str, str]] = {
    "AUTHDIFF-RULE-011": {
        "summary": "Pin MCP launcher package version",
        "diff": (
            '- "args": ["-y", "pkg"]\n'
            '+ "args": ["-y", "pkg@1.2.3"]  # pin exact version or digest\n'
        ),
    },
    "AUTHDIFF-RULE-012": {
        "summary": "Replace literal MCP env secret with placeholder",
        "diff": (
            '- "API_KEY": "sk-live-..."\n'
            '+ "API_KEY": "${API_KEY}"  # inject from host secret store\n'
        ),
    },
    "AUTHDIFF-RULE-013": {
        "summary": "Upgrade remote MCP URL to HTTPS",
        "diff": '- "url": "http://..."\n+ "url": "https://..."\n',
    },
    "AUTHDIFF-RULE-015": {
        "summary": "Remove download-and-execute; vendor a pinned script",
        "diff": (
            "- curl https://example/install.sh | bash\n"
            "+ # use a local pinned script checked into the repo\n"
        ),
    },
    "AUTHDIFF-RULE-016": {
        "summary": "Avoid pull_request_target for untrusted agent steps",
        "diff": (
            "- on: pull_request_target\n+ on: pull_request  # keep secrets off fork PR code paths\n"
        ),
    },
    "AUTHDIFF-RULE-017": {
        "summary": "Remove permission-bypass / auto-approve flags",
        "diff": (
            "- --dangerously-skip-permissions\n"
            "+ # require interactive approval for privileged tool use\n"
        ),
    },
    "AUTHDIFF-RULE-002": {
        "summary": "Stop inheriting broad host env into MCP process",
        "diff": (
            '- "env": { ...full host inheritance... }\n'
            '+ "env": { "NEEDFUL_ONLY": "${NEEDFUL_ONLY}" }\n'
        ),
    },
}


@dataclass(slots=True)
class HardenProposal:
    finding_id: str
    rule_id: str
    title: str
    summary: str
    diff: str
    evidence_strength: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "title": self.title,
            "summary": self.summary,
            "diff": self.diff,
            "evidence_strength": self.evidence_strength,
            "apply_supported": False,
        }


def propose_patches(findings_doc: dict[str, Any]) -> list[HardenProposal]:
    out: list[HardenProposal] = []
    for finding in findings_doc.get("findings") or []:
        if not is_gate_finding(finding):
            continue
        rule_id = str(finding.get("rule_id") or "")
        template = _PATCH_TEMPLATES.get(rule_id)
        if template is None:
            continue
        strength = str(finding.get("evidence_strength") or "")
        if strength == "NAME_MARKER":
            continue
        out.append(
            HardenProposal(
                finding_id=str(finding.get("finding_id") or ""),
                rule_id=rule_id,
                title=str(finding.get("title") or ""),
                summary=template["summary"],
                diff=str(finding.get("fix_snippet") or template["diff"]),
                evidence_strength=strength,
            )
        )
    return out


def render_harden_report(proposals: list[HardenProposal]) -> str:
    lines = [
        "authdiff harden — least-privilege patches (dry-run)",
        "Patches can break working setups. Review before applying.",
        "Automatic file apply is not enabled in this release.",
        "",
    ]
    if not proposals:
        lines.append("No patch templates matched gated findings.")
        lines.append(
            "Run `authdiff scan` first, or there may be nothing high-confidence to auto-fix."
        )
        return "\n".join(lines)

    for prop in proposals:
        lines.append(f"## {prop.finding_id} ({prop.rule_id}) [{prop.evidence_strength}]")
        lines.append(prop.title)
        lines.append(f"Intent: {prop.summary}")
        lines.append("```diff")
        lines.append(prop.diff.rstrip())
        lines.append("```")
        lines.append("")
    lines.append("Copy the snippets above into a PR manually.")
    return "\n".join(lines)


def run_harden(
    *,
    findings_path: Path,
    apply: bool = False,
) -> tuple[str, int]:
    """Load findings and emit dry-run patch proposals.

    ``apply=True`` is rejected with exit 2 so callers cannot accidentally believe
    files were rewritten.
    """
    if not findings_path.is_file():
        return (
            f"Missing findings at {findings_path}. Run `authdiff scan` or `authdiff doctor` first.",
            1,
        )
    doc = read_json(findings_path)
    if not isinstance(doc, dict):
        return "findings.json must be a JSON object", 1
    proposals = propose_patches(doc)
    text = render_harden_report(proposals)
    if apply:
        text += (
            "\n\nERROR: automatic --apply is disabled in this release. "
            "Use the dry-run snippets and apply patches manually."
        )
        return text, 2
    return text, 0
