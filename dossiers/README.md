# Public Trust Dossiers

Browse the catalog at [`CATALOG.json`](CATALOG.json). Each entry is a package,
URL, or GitHub target you can inspect without installing auctelis:

```bash
uvx --from "git+https://github.com/roham-amd/auctelis.git@v0.1.11#subdirectory=tools" auctelis inspect <target>
```

Or [request a dossier](../.github/ISSUE_TEMPLATE/inspect_request.yml) via
IssueOps. Maintainers regenerate committed Markdown dossiers with:

```bash
uv run --directory tools auctelis-dev build dossiers
```

| Component | Target | Verdict | Red Flags | Dossier |
| --- | --- | --- | --- | --- |
| server-filesystem | npm:@modelcontextprotocol/server-filesystem | _run build dossiers_ | — | — |
| server-github | npm:@modelcontextprotocol/server-github | _run build dossiers_ | — | — |
| server-memory | npm:@modelcontextprotocol/server-memory | _run build dossiers_ | — | — |
| server-puppeteer | npm:@modelcontextprotocol/server-puppeteer | _run build dossiers_ | — | — |
| server-brave-search | npm:@modelcontextprotocol/server-brave-search | _run build dossiers_ | — | — |
| server-sqlite | npm:@modelcontextprotocol/server-sqlite | _run build dossiers_ | — | — |
| server-sequential-thinking | npm:@modelcontextprotocol/server-sequential-thinking | _run build dossiers_ | — | — |
| server-everything | npm:@modelcontextprotocol/server-everything | _run build dossiers_ | — | — |
| mcp-server-fetch | pypi:mcp-server-fetch | _run build dossiers_ | — | — |
| auctelis | https://github.com/roham-amd/auctelis | _run build dossiers_ | — | — |
