# Recipe: staging boundary (not part of passive audit)

Runtime validation is **opt-in** and **out of band** from the default AESA passive procedure.

Checklist before any dynamic test:

- [ ] Written authorization and scope reference recorded
- [ ] Disposable environment; no production credentials or data
- [ ] Default-deny egress with explicit allowlist for test endpoints only
- [ ] Synthetic identities and canary secrets only
- [ ] Abort conditions and resource limits defined
- [ ] Results captured in `runtime-test-record.schema.json` and linked `RUNTIME` evidence

The passive audit JSON summary must not imply runtime proof unless evidence is attached.

See [`docs/runtime-validation/README.md`](../runtime-validation/README.md).
