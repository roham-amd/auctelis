"""Deterministic security engine for authdiff."""

from authdiff.security.engine import ScanResult, run_security_scan
from authdiff.security.gating import GATE_FINDING_CLASSES, compute_exit_code, is_gate_finding
from authdiff.security.models import Capability, Evidence, Finding, Relationship

__all__ = [
    "GATE_FINDING_CLASSES",
    "Capability",
    "Evidence",
    "Finding",
    "Relationship",
    "ScanResult",
    "compute_exit_code",
    "is_gate_finding",
    "run_security_scan",
]
