"""Host-level authority map (`auctelis doctor`).

`doctor` is an alias for the Authority Watch first screen: declared config on
this machine, diffed against the last human seal. It no longer prints a findings
wall; rule IDs are annotations, not the product.

Host discovery/staging lives in :mod:`auctelis.host_scan`; the names are
re-exported here for callers that used the pre-0.4 location.
"""

from __future__ import annotations

from pathlib import Path

from auctelis.host_scan import (
    HOST_RELATIVE_SURFACES,
    HostSurface,
    discover_host_surfaces,
    stage_all_host_surfaces,
)
from auctelis.jsonio import write_json

__all__ = [
    "HOST_RELATIVE_SURFACES",
    "HostSurface",
    "discover_host_surfaces",
    "run_doctor",
    "run_doctor_since_lock",
    "stage_all_host_surfaces",
]


def run_doctor_since_lock(
    *,
    home: Path | None = None,
    lock_file: Path | None = None,
) -> tuple[str, int]:
    """Backwards-compatible alias for the one-screen delta."""
    return run_doctor(home=home, since_lock=True, lock_file=lock_file)


def run_doctor(
    *,
    home: Path | None = None,
    output_dir: Path | None = None,
    fail_on: str | None = None,
    since_lock: bool = False,
    lock_file: Path | None = None,
    delta_only: bool = False,
) -> tuple[str, int]:
    """Render the Authority Watch screen; return (text, exit_code).

    ``doctor`` and ``doctor --since-lock`` are the same screen. Exit 1 only when
    the host authority changed since the seal (or when ``--fail-on`` is set and
    the current scan matches it). No lock is a valid empty baseline — exit 0.
    """
    from auctelis.watch import build_watch_report, render_watch

    report, cards, scan = build_watch_report(home=home, lock_file=lock_file)
    code = 2 if report.get("error") else (1 if report.get("meaningful") else 0)
    if fail_on in {"high", "any"} and scan is not None:
        from auctelis.security.gating import compute_exit_code

        code = max(
            code,
            compute_exit_code(
                fail_on,
                findings=scan.findings,
                coverage=scan.coverage if isinstance(scan.coverage, dict) else None,
            ),
        )
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "watch-report.json", report)
    command = "auctelis doctor --since-lock" if since_lock else "auctelis doctor"
    return render_watch(report, cards, command=command, delta_only=delta_only), code
