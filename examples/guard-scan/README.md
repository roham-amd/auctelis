# Sample auctelis annotation artifacts (frozen)

Historical artifacts from `examples/demo-vulnerable` (generated under 0.1.0).
JSON/SARIF blobs are intentionally frozen for contract shape. Product path:

```bash
auctelis check examples/demo-vulnerable
auctelis demo
# Maintainer regenerate (optional):
auctelis-dev scan examples/demo-vulnerable -o examples/guard-scan --full --fail-on never
```

These illustrate findings / Authority Diff / SBOM shape.
They are **not** a clean bill of health for any real repository.
