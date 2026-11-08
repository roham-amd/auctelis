# Radical alternatives (MVP status)

From the strategic review. Primary product path remains
Authority Lock + PR Gate — see [`../ROADMAP.md`](../ROADMAP.md) and
[`../PRODUCT.md`](../PRODUCT.md). Items below are **opt-in / deferred**, not
the default experience.

## Three serious long-term pivots (do not build as the product yet)

### 1. Agent Authority Passport / Manifest standard

Open standard for describing the authority an integration requires. Publishers
ship manifests; scanners independently observe; registries and IDEs consume.
Shipped seed: [`../AGENT-AUTHORITY-MANIFEST.md`](../AGENT-AUTHORITY-MANIFEST.md).
Full ecosystem adoption remains deferred.

### 2. Runtime Agent Capability Broker

Local enforcement that mediates MCP/filesystem/shell/network by policy.
Partial opt-in today: `authdiff run` (env scrub + lock path recording) — **not**
a sandbox. Full stdio MCP proxy deferred.

### 3. Agent Ecosystem Change Intelligence

Service that tracks upstream authority changes for skills/MCP/plugins and alerts
consumers before upgrades. Deferred until lock+gate adoption is proven.

## Other deferred ideas

- Org-wide SaaS authority dashboard
- Marketplace / certification-lite badges
- MCP audit-assistance server exposing unrestricted filesystem tools
- Prompt-only kit as a competing primary product (kept under `archive/methodology/`)

## Shipped opt-in MVPs

## 1. Authority broker — `authdiff run`

```bash
authdiff run --lock AUTHORITY.lock -- npx -y @modelcontextprotocol/server-everything
```

Scrubs secret-shaped env vars and records the lock path for the child. Full
stdio MCP frame proxy is deferred; pair with `authdiff snapshot` to pin tool
description hashes.

## 2. Attack-replay corpus — `examples/attack-replay/`

Inert malicious configs aimed at `127.0.0.1:9/canary`. Use as the regression
suite other scanners measure against:

```bash
authdiff scan examples/attack-replay/01-sessionstart-curl-env
```

## 3. AUTHORITY spec + LSP stub — `authdiff lsp-validate`

JSON Schemas:

- [`../../schemas/authority-lock.schema.json`](../../schemas/authority-lock.schema.json)
- [`../../schemas/authority-policy.schema.json`](../../schemas/authority-policy.schema.json)
- [`../../schemas/agent-authority-manifest.schema.json`](../../schemas/agent-authority-manifest.schema.json)
