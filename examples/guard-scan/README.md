# Sample auctelis scan artifacts (frozen)

Historical artifacts from `examples/demo-vulnerable` (generated under 0.5.0).
JSON/SARIF blobs are intentionally frozen for contract shape; regenerate with a
current tag when you need fresh numbers:

```bash
auctelis check examples/demo-vulnerable
auctelis scan examples/demo-vulnerable -o examples/guard-scan --full --fail-on never
```

These illustrate the findings / one-verdict Authority Diff / SBOM contract shape.
They are **not** a clean bill of health for any real repository.
