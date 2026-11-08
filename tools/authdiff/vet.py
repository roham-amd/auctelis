"""Pre-install verdict for a candidate skill/MCP package (`authdiff vet` / `open`).

Clones a remote Git URL into a throwaway directory with hooks disabled, no
submodules, and no LFS smudge — then runs a Guard scan. Never executes target
application code.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from authdiff.security.decision import compute_decision
from authdiff.security.gating import is_gate_finding
from authdiff.security.scan import run_scan

# owner/repo, github.com/owner/repo, https://github.com/owner/repo(.git|/tree/...),
# git@github.com:owner/repo.git
_GITHUB_SHORTHAND = re.compile(
    r"^(?:https?://github\.com/|git@github\.com:|github\.com/)?"
    r"(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE,
)
_ALLOWED_GIT_HOSTS = frozenset({"github.com"})


def resolve_vet_source(source: str) -> tuple[str, str]:
    """Return (kind, normalized) where kind is ``path`` or ``git``."""
    raw = source.strip()
    as_path = Path(raw).expanduser()
    if as_path.exists():
        return "path", str(as_path.resolve())
    if "://" in raw or raw.startswith("git@") or _GITHUB_SHORTHAND.match(raw):
        return "git", _normalize_git_url(raw)
    raise ValueError(
        f"Cannot resolve vet source {source!r}: expected a local path or GitHub URL/shorthand"
    )


def _normalize_git_url(raw: str) -> str:
    """Normalize GitHub shorthand / web URLs to https clone URLs."""
    text = raw.strip()
    # Strip common web UI suffixes before matching.
    text = re.sub(r"/(?:tree|blob|commit|releases|issues)/.*$", "", text, flags=re.IGNORECASE)
    match = _GITHUB_SHORTHAND.match(text)
    if match:
        owner, repo = match.group("owner"), match.group("repo")
        if owner.lower() == "github.com":
            raise ValueError(
                f"Ambiguous GitHub URL {raw!r}: use owner/repo or https://github.com/owner/repo"
            )
        return f"https://github.com/{owner}/{repo}.git"
    if text.startswith("git@"):
        # git@host:owner/repo.git — only github.com allowed below
        return text if text.endswith(".git") else f"{text}.git"
    if "://" in text:
        return text
    raise ValueError(f"Cannot normalize git URL {raw!r}")


def _assert_allowed_clone_url(url: str) -> None:
    """Refuse non-https / non-allowlisted hosts (attacker-influenced strings)."""
    if url.startswith("git@"):
        # git@github.com:owner/repo.git
        host = url.split("@", 1)[1].split(":", 1)[0].lower()
        if host not in _ALLOWED_GIT_HOSTS:
            raise ValueError(f"Refusing git host {host!r}; allowed: {sorted(_ALLOWED_GIT_HOSTS)}")
        return
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Refusing non-https clone scheme {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_GIT_HOSTS:
        raise ValueError(f"Refusing git host {host!r}; allowed: {sorted(_ALLOWED_GIT_HOSTS)}")


def _safe_clone(url: str, dest: Path) -> None:
    """Shallow clone with supply-chain safety flags; never run remote hooks."""
    _assert_allowed_clone_url(url)
    dest.mkdir(parents=True, exist_ok=True)
    # Empty hooks dir works on Windows and POSIX (avoids /dev/null hooksPath).
    hooks = dest.parent / "empty-hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    cmd = [
        "git",
        "-c",
        f"core.hooksPath={hooks}",
        "-c",
        "filter.lfs.smudge=",
        "-c",
        "filter.lfs.required=false",
        "-c",
        "protocol.file.allow=never",
        "-c",
        "protocol.ext.allow=never",
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--no-recurse-submodules",
        "--",
        url,
        str(dest),
    ]
    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


# Paths that grant project-scoped authority when a developer opens a clone.
_QUARANTINE_GLOBS = (
    ".cursor/mcp.json",
    ".mcp.json",
    ".vscode/mcp.json",
    ".claude/settings.json",
    ".claude/settings.local.json",
    "hooks.json",
)


def quarantine_agent_authority(root: Path) -> list[str]:
    """Rename project agent-authority files so opening the tree is safer.

    Used after a remote ``vet``/``open`` clone (and optionally ``--keep-clone``).
    Does not delete evidence — appends ``.authdiff-quarantined`` so scanners can still
    read the original content via the renamed path if needed. Returns relative paths
    that were quarantined.
    """
    quarantined: list[str] = []
    root = root.resolve()
    candidates: list[Path] = []
    for rel in _QUARANTINE_GLOBS:
        path = root / rel
        if path.is_file():
            candidates.append(path)
    # Hook directories / Claude hooks trees
    for rel in ("hooks", ".claude/hooks", ".cursor/hooks"):
        path = root / rel
        if path.is_dir():
            candidates.append(path)
    for path in candidates:
        if path.name.endswith(".authdiff-quarantined"):
            continue
        dest = path.with_name(path.name + ".authdiff-quarantined")
        if dest.exists():
            continue
        try:
            path.rename(dest)
        except OSError:
            continue
        try:
            quarantined.append(str(dest.relative_to(root)).replace("\\", "/"))
        except ValueError:
            quarantined.append(str(dest))
    return quarantined


def _verdict(scan: Any) -> str:
    """Map shared gate decision onto vet labels (never quiet-accept unparsed configs)."""
    decision = compute_decision(
        scan.findings,
        coverage=getattr(scan, "coverage", None),
    )
    if decision == "BLOCK":
        return "REJECT"
    if decision == "REVIEW":
        return "REVIEW"
    # Prefer an honest label: no gated findings in scope is not "ACCEPT".
    return "NO_FINDINGS_IN_SCOPE"


def render_vet_report(
    *,
    source: str,
    resolved: str,
    scan: Any,
    coverage_note: str,
    quarantined: list[str] | None = None,
) -> str:
    gated = [f for f in scan.findings if is_gate_finding(f) and not getattr(f, "suppressed", False)]
    verdict = _verdict(scan)
    lines = [
        "authdiff vet — pre-install authority verdict",
        f"source: {source}",
        f"resolved: {resolved}",
        f"verdict: {verdict}",
        coverage_note,
    ]
    if quarantined:
        lines.append(
            "quarantine: neutralized project authority files "
            f"({len(quarantined)}) → *.authdiff-quarantined"
        )
        for rel in quarantined[:8]:
            lines.append(f"  - {rel}")
        if len(quarantined) > 8:
            lines.append(f"  - … +{len(quarantined) - 8} more")
    lines.extend(
        [
            "",
            "Authority introduced (gated findings first):",
        ]
    )
    show = gated or [f for f in scan.findings if f.finding_class != "CAPABILITY"][:5]
    if not show:
        lines.append("  (no gated EXPOSURE/SECURITY_FINDING — still check coverage gaps)")
    for finding in show[:12]:
        pin = f" [{finding.evidence_strength}]" if finding.evidence_strength else ""
        lines.append(f"  - {finding.severity}{pin} {finding.rule_id}: {finding.title}")
        if finding.fix_snippet:
            lines.append(f"    fix: {finding.fix_snippet}")
        if finding.verify_in_60s:
            lines.append(f"    verify: {finding.verify_in_60s}")
    caps = sum(1 for f in scan.findings if f.finding_class == "CAPABILITY")
    lines.append("")
    lines.append(
        f"summary: components="
        f"{len(scan.inventory.get('components') or [])} "
        f"gated={len(gated)} capabilities={caps}"
    )
    lines.append("Passive scan only — did not install packages, start MCP servers, or run hooks.")
    return "\n".join(lines)


def run_vet(
    source: str,
    *,
    output_dir: Path | None = None,
    keep_clone: bool = False,
) -> tuple[str, int]:
    kind, resolved = resolve_vet_source(source)
    tmp_root: Path | None = None
    target: Path
    try:
        if kind == "path":
            target = Path(resolved)
        else:
            try:
                _assert_allowed_clone_url(resolved)
            except ValueError as exc:
                return f"authdiff vet refused source: {exc}", 2
            tmp_root = Path(tempfile.mkdtemp(prefix="authdiff-vet-"))
            target = tmp_root / "src"
            try:
                _safe_clone(resolved, target)
            except subprocess.CalledProcessError as exc:
                err = (exc.stderr or exc.stdout or str(exc)).strip()
                return f"authdiff vet failed to clone {resolved}: {err}", 2
            except subprocess.TimeoutExpired:
                return f"authdiff vet timed out cloning {resolved}", 2
            except FileNotFoundError:
                return "authdiff vet requires `git` on PATH for remote sources.", 2
            except ValueError as exc:
                return f"authdiff vet refused source: {exc}", 2

        out = output_dir or (tmp_root / "authdiff-out" if tmp_root else Path("authdiff-out"))
        # Never trust target policy for pre-install verdicts.
        scan, _payload, code = run_scan(target, output_dir=out, fail_on="high", policy=None)
        # Quarantine after scan so findings still see original paths; then neutralize
        # hooks/MCP so --keep-clone / local inspect cannot auto-load project authority.
        quarantined: list[str] = []
        if kind == "git":
            quarantined = quarantine_agent_authority(target)
        cov = scan.coverage or {}
        supported = cov.get("deterministically_discovered") or cov.get("supported") or "?"
        not_verified = cov.get("not_verified") or []
        coverage_note = (
            f"coverage: deterministic={supported}; "
            f"NOT VERIFIED families={len(not_verified)} "
            "(no findings ≠ safe on MANUAL_ONLY/PARTIAL surfaces)"
        )
        text = render_vet_report(
            source=source,
            resolved=resolved,
            scan=scan,
            coverage_note=coverage_note,
            quarantined=quarantined,
        )
        # Exit: 0 no gated findings in scope, 1 review/reject, 2 tooling failure.
        # ``code`` from run_scan already fails closed on unparsed configs.
        verdict = _verdict(scan)
        exit_code = 0 if verdict == "NO_FINDINGS_IN_SCOPE" else 1
        if code and exit_code == 0:
            exit_code = code
        return text, exit_code
    finally:
        if tmp_root is not None and not keep_clone:
            shutil.rmtree(tmp_root, ignore_errors=True)
