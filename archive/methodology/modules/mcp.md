# Module: MCP Servers and Clients

**AESA module ID:** `MCP`  
**Procedure reference:** Section 10.4 of `prompts/02-modules.md` (core: `prompts/01-core-prompt.md`)
**Applies when:** component type is `MCP Server`, `MCP Client`, or a host configuration that registers MCP endpoints/tools.

MCP assessment is mandatory for MCP components. Identify exact protocol revision, SDK/version, transport, endpoint or launch command, server identity, capability set, negotiated extensions, and implementation-specific behavior. Retrieve the official specification corresponding to the implementation and audit date. Never apply requirements from another revision without explaining compatibility and applicability.

## Checklist

### A. Protocol and version correctness

- [ ] Protocol revision recorded
- [ ] Client/server SDK and versions recorded
- [ ] Release date / lifecycle status of optional or experimental features recorded
- [ ] Version negotiation and metadata behavior reviewed
- [ ] Mandatory core vs optional / experimental / deprecated / implementation-specific behavior distinguished

### B. Identity and discovery

- [ ] Server name/identity, publisher, package identity recorded
- [ ] Endpoint ownership and runtime identity reviewed
- [ ] Metadata provenance and discovery path reviewed
- [ ] Each tool bound to originating server identity
- [ ] Impersonation, name collisions, tool shadowing, endpoint substitution assessed

### C. STDIO / subprocess transport

- [ ] Executable path / pinned package or binary reviewed
- [ ] Command, arguments, shell wrappers reviewed
- [ ] Environment inheritance and credentials reviewed
- [ ] Working directory, filesystem permissions, child processes reviewed
- [ ] Launch policy, update path, host restriction capability reviewed
- [ ] Note: STDIO does **not** imply isolation

### D. HTTP-based and other remote transports

- [ ] TLS and hostname validation reviewed
- [ ] Redirect / origin / host validation reviewed
- [ ] OAuth/OIDC issuer, audience, scopes, token lifecycle reviewed
- [ ] Credential forwarding and header handling reviewed
- [ ] DNS rebinding, private-network restrictions, SSRF assessed
- [ ] Rate limits, response sizes, timeouts, cancellation, errors reviewed
- [ ] Tokens never transmitted to arbitrary endpoints

### E. Capabilities and extensions

- [ ] Tools, resources, prompts, sampling, elicitation, roots, tasks, notifications, logging, completions reviewed as applicable
- [ ] Extensions / Apps / UI surfaces reviewed if negotiated
- [ ] Each capability classified: mandatory / optional / experimental / deprecated / implementation-specific
- [ ] Authorization, side effects, provenance, recursion, disclosure, deception assessed

### F. Tools, resources and prompts

- [ ] Name, description, input/output schema, annotations, defaults reviewed per tool
- [ ] Side effects, errors, authorization, idempotency, origin identity reviewed
- [ ] URI parsing, scheme/host allowlists, path traversal reviewed
- [ ] Content provenance and untrusted-data separation reviewed
- [ ] Note: server-origin output is **not** automatically trusted

### G. Host-side responsibility

- [ ] Host authenticates/binds server identity
- [ ] Permissions scoped; server provenance preserved
- [ ] Metadata-change validation present
- [ ] Action/target displayed accurately to users
- [ ] Untrusted-output labels retained
- [ ] Unapproved execution blocked outside the LLM
- [ ] Unauthorized chaining prevented
- [ ] Emergency disablement supported

## Common evidence blockers

- Protocol revision unknown
- Transport or launch command not evidenced
- Consumed package/binary digest `NOT VERIFIED`
- Host permission model unavailable
- Runtime metadata drift not observed → mark `NOT VERIFIED`

## Decision reminders

- Source review ≠ artifact verification
- Server assertions ≠ host enforcement
- Do not contact operational MCP endpoints during a passive audit
