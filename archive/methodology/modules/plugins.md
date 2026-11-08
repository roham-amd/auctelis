# Module: Plugins and Connectors

**AESA module ID:** `PLUGINS`  
**Procedure reference:** Section 10.3 of `prompts/02-modules.md` (core: `prompts/01-core-prompt.md`)
**Applies when:** component type is `Plugin`, `Connector`, `IDE Extension`, or equivalent marketplace/extension package.

Plugins and Connectors are not trusted merely because they use legitimate credentials or appear in a marketplace.

## Inspection surfaces

- Manifest / package metadata / publisher identity
- Package contents and entrypoints
- Install and update mechanisms
- Declared capabilities and permissions
- Authentication / authorization paths
- External services, webhooks, background processes
- OpenAPI / HTTP operation surfaces where present

## Checklist

- [ ] Exact publisher, package coordinate, version, digest recorded (or `NOT VERIFIED`)
- [ ] Installation and auto-update policy reviewed
- [ ] Entrypoints and privileged APIs inventoried
- [ ] OpenAPI operations / HTTP methods reviewed for excessive agency
- [ ] Arbitrary URL handling / SSRF risk assessed (inventory destinations; do not probe)
- [ ] Object/function authorization reviewed (labels like “read-only” are not proof)
- [ ] OAuth scopes, token handling, redirects reviewed
- [ ] Webhook authentication, signatures, replay protections reviewed
- [ ] API-key / secret handling reviewed (record type/location only; never values)
- [ ] Telemetry, retention, external data processing reviewed
- [ ] Hidden endpoints and plugin-to-plugin trust assessed
- [ ] Source-to-artifact traceability assessed separately from source review

## Supply-chain reminders

- Marketplace listing metadata ≠ package authenticity
- Source review alone cannot pass artifact gates (C-G03–C-G05)
- Mutable tags / unpinned updates are evidence gaps for production suitability

## Passive-audit constraints

- Do not install the plugin, open it in an IDE that may auto-run tasks, or authenticate to its services.
- Do not validate live credentials or contact operational endpoints.
