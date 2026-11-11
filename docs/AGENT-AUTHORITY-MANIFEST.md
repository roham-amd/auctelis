# Agent Authority Manifest (legacy)

Compact, vendor-neutral declaration of the authority an AI-agent integration
**requires** or **exposes**. In 0.3.0 the product source of truth is
[`AUTHORITY.lock`](AUTHORITY-LOCK.md); the experimental `AUTHORITY.yml` /
`init-manifest` / `verify-manifest` CLI was removed.

authdiff still exports an independently observed
[`authority-sbom.json`](../tools/authdiff/export/authority_sbom.py) from
`authdiff scan` when full artifacts are enabled.

Schema (if present in checkout):
[`../schemas/agent-authority-manifest.schema.json`](../schemas/agent-authority-manifest.schema.json)

## Current workflow

```bash
authdiff scan .                   # findings + inventory (+ SBOM with --full)
authdiff lock .                   # seal AUTHORITY.lock
authdiff gate . --base-lock path/to/base.lock
```

## Trust rule

A publisher-signed declaration is still **untrusted** until an independent scanner
observes the artifact. Differences between declared and observed capabilities
are the security signal.

## Layers

Declarations record **Declared** intent. Scanners fill **Configured/Observed**
fields. **Effective** and **Verified** require host or authorized runtime evidence.
