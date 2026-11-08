# A2A (Agent-to-Agent) security module

Apply when the ecosystem exposes **A2A** peers, Agent Cards, task APIs, or multi-agent orchestration using the A2A protocol. Generic subagent guidance in `subagents.md` does not replace these checks.

## Applicability

- `N/A` only with evidence that no A2A endpoints, Agent Cards, or A2A client registrations exist in scope.
- Record exact **protocol version**, transport (HTTP/gRPC), and negotiated extensions.

## A. Agent Card integrity and discovery

- Agent Card URL, issuer, version, and signature (if present).
- Card substitution, stale cache, and discovery endpoint ownership.
- TLS certificate identity vs advertised agent identity.
- Unsupported or deprecated authentication schemes explicitly marked `NOT VERIFIED`.

## B. Authentication and caller identity

- Authentication scheme per operation (not only at connection time).
- Caller-scoped task and resource authorization; reject cross-tenant task enumeration assumptions.
- Token audience, expiry, replay, and binding to the requesting principal.

## C. Task and message authorization

- Task creation, status, result retrieval, and cancellation require matching caller scope.
- Validate that summarized or delegated results preserve origin identity.
- Treat inter-agent messages as untrusted until authenticated and authorized.

## D. Extensions and capabilities

- Record optional/experimental extensions separately from core requirements.
- Do not mark a control passed from narrative Agent Card text alone.

## Evidence and limitations

- Static review of Agent Cards and client configuration is **source-static** evidence.
- Runtime authorization enforcement requires separately authorized staging tests (`NOT VERIFIED` until performed).

## Related corpus families

See `tests/corpus/README.md` — A2A fixture family (pilot cases planned; not all protocol revisions covered).
