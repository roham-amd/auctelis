# Module — CI/CD agent surfaces

Assess workflows, reusable workflows, deployment authority, and secret inheritance
when agent ecosystems are built or deployed via CI.

## Security questions

1. `permissions:` and token scopes on workflows touching agent configs.
2. Trust in reusable workflows / third-party Actions (pin digest?).
3. Secret inheritance into jobs that inventory or “test” agent tools.
4. Whether CI can modify production agent registrations.
5. Artifact provenance for published skills/MCP packages.

## Guardrail

Passive AESA mode must not execute target workflows. Treat workflow YAML as
`SOURCE_STATIC` evidence only unless RUNTIME tests are separately authorized.
