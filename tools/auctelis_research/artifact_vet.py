"""Re-exports artifact vetting from the product security package."""

from __future__ import annotations

from auctelis.security.artifact_vet import (
    ArtifactFinding,
    ArtifactReport,
    parse_artifact_spec,
    run_artifact_vet,
    vet_npm,
    vet_pypi,
    write_artifact_report,
)

__all__ = [
    "ArtifactFinding",
    "ArtifactReport",
    "parse_artifact_spec",
    "run_artifact_vet",
    "vet_npm",
    "vet_pypi",
    "write_artifact_report",
]
