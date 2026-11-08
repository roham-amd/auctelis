# Agent Authority Manifest

Compact, vendor-neutral declaration of the authority an AI-agent integration
**requires** or **exposes**. authdiff drafts and verifies manifests; it also
exports an independently observed [`authority-sbom.json`](../tools/authdiff/export/authority_sbom.py).

Schema: [`../schemas/agent-authority-manifest.schema.json`](../schemas/agent-authority-manifest.schema.json)

## Commands

```bash
authdiff init-manifest .          # draft AUTHORITY.yml from observed inventory
authdiff verify-manifest .        # fail on undeclared component growth
authdiff scan .                   # also writes authdiff-out/authority-sbom.json
```

## Trust rule

A publisher-signed manifest is still **untrusted** until an independent scanner
observes the artifact. Differences between declared and observed capabilities
are the security signal.

## Layers

Manifests record **Declared** intent. Scanners fill **Configured/Observed**
fields. **Effective** and **Verified** require host or authorized runtime evidence.
