from __future__ import annotations

import hashlib
import re

from authdiff.paths import repo_root


def _read(rel: str) -> str:
    return (repo_root() / rel).read_text(encoding="utf-8")


def _slice_from_heading(text: str, heading_prefix: str, *, end_before: str | None = None) -> str:
    start = text.find(heading_prefix)
    if start < 0:
        raise ValueError(f"Heading not found: {heading_prefix!r}")
    chunk = text[start:]
    if end_before:
        end = chunk.find(end_before, len(heading_prefix))
        if end > 0:
            chunk = chunk[:end]
    return chunk.rstrip() + "\n"


def _strip_core_kit_preamble(core: str) -> str:
    """Remove kit-only preamble; start at Section 0."""
    marker = "# 0. PURPOSE AND OPERATING MODEL"
    idx = core.find(marker)
    if idx < 0:
        raise ValueError("Core prompt missing Section 0")
    return core[idx:]


def _trim_block(text: str) -> str:
    return text.strip() + "\n\n"


def assemble_monolith() -> str:
    header = _read("canonical/prompt/monolithic-header.md").rstrip() + "\n\n"
    core = _read("archive/methodology/prompts/01-core-prompt.md")
    modules = _read("archive/methodology/prompts/02-modules.md")
    contract = _read("archive/methodology/prompts/03-report-contract.md")

    core_body = _strip_core_kit_preamble(core)
    part_through_9 = _trim_block(
        _slice_from_heading(core_body, "# 0. PURPOSE", end_before="# 10. SPECIALIZED")
    )
    modules_body = _trim_block(_slice_from_heading(modules, "# 10. SPECIALIZED"))
    part_11_through_21 = _slice_from_heading(
        core_body, "# 11. ADVANCED", end_before="# 22. MACHINE-READABLE"
    )
    part_11_through_21 = re.sub(r"^---\s*\n+", "", part_11_through_21.lstrip())
    part_11_through_21 = _trim_block(part_11_through_21)
    contract_body = _trim_block(_slice_from_heading(contract, "# 22. MACHINE-READABLE"))
    part_24_end = _slice_from_heading(core_body, "# 24. FINAL SELF-INTEGRITY").rstrip() + "\n"

    return "".join(
        [
            header,
            part_through_9,
            modules_body,
            "---\n\n",
            part_11_through_21,
            contract_body,
            part_24_end,
        ]
    )


def monolith_sha256(content: str | None = None) -> str:
    text = content if content is not None else assemble_monolith()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_monolith(*, check_only: bool = False) -> dict:
    manifest = repo_root() / "canonical" / "prompt-kit.manifest.json"
    import json

    cfg = json.loads(manifest.read_text(encoding="utf-8"))
    out_rel = cfg["monolithic_output"]
    out_path = repo_root() / out_rel
    generated = assemble_monolith()
    existing = out_path.read_text(encoding="utf-8") if out_path.is_file() else ""

    gen_hash = monolith_sha256(generated)
    exist_hash = hashlib.sha256(existing.encode("utf-8")).hexdigest() if existing else None

    if check_only:
        if gen_hash != exist_hash:
            raise SystemExit(
                f"Monolith drift: {out_rel} does not match generated content. "
                f"Run: authdiff build prompts --write"
            )
        return {"status": "ok", "path": out_rel, "sha256": gen_hash}

    out_path.write_text(generated, encoding="utf-8")
    return {"status": "written", "path": out_rel, "sha256": gen_hash}
