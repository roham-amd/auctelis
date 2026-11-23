# Auctelis

**Decide in 10 seconds whether you can trust an MCP server, skill, hook, or plugin.**

Zero-install: browse [`dossiers/CATALOG.json`](dossiers/CATALOG.json) or
[Request a dossier](.github/ISSUE_TEMPLATE/inspect_request.yml).

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md) · Reach: [`docs/REACH.md`](docs/REACH.md)

---

## First ten minutes

```bash
# 1. Trust dossier for a package (aha):
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect npm:@modelcontextprotocol/server-filesystem

# 2. Read-only audit of local agent configs:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect --local

# 3. Authority Diff vs a git base:
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis diff --base origin/main
```

Public docs: [`INSTALL`](docs/INSTALL.md) · [`PRODUCT`](docs/PRODUCT.md) ·
[`REACH`](docs/REACH.md) · [`AUTHORITY-LOCK`](docs/AUTHORITY-LOCK.md) ·
[`AUCTELIS-GATE`](docs/AUCTELIS-GATE.md) · [index](docs/DOCUMENTATION-INDEX.md).

Pilots: [`docs/pilots/`](docs/pilots/).

---

## License

MIT — see [`LICENSE`](LICENSE).
