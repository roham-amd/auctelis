# authdiff pilot repositories

Pilot scans prove that developers can install AESA and get a useful answer on
real (or realistic) agent ecosystems. Pilot results are **adoption evidence**,
not AgentSecBench external evaluation evidence.

## Quick run

```bash
cd tools
uv sync --locked
uv run authdiff pilots run
```

Artifacts land in `docs/pilots/results/<pilot-id>/` plus `summary.md`.

## Manifest

[`manifest.json`](manifest.json) lists enabled targets. Add independent
repositories as absolute paths only when you have explicit authorization:

```json
{
  "id": "acme-agent-platform",
  "path": "C:/pilots/acme-agent-platform",
  "absolute": true,
  "kind": "external",
  "enabled": true,
  "notes": "Authorized pilot — contact alice@acme.example"
}
```

## Checklist (per external pilot)

1. Written authorization to scan (scope + commit).
2. Record product/tooling versions used.
3. Capture false positives, missed detections, install failures.
4. File issues against AESA; do not silently retune rules without fixtures.
5. Do **not** count pilot scans as AgentSecBench `external` intakes.

## Relationship to AgentSecBench

| Program | Counts toward |
| --- | --- |
| `aesa pilots run` | Guard productization / adoption |
| `aesa benchmark intake --provenance external` | Independent LLM audit evaluation (N) |
