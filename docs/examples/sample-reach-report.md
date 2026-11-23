# Auctelis Fleet Agent Reach Report

> Passive scan of declared agent config, not a certificate.

## Summary

**3 repositories, 2 at tier 2.** tier0=0 · tier1=2 · tier2=2
- **Watching:** 1 of 3 repos · unwatched tier-2: 2

- **browser** in `example-org/frontend` (`.cursor/mcp.json`) — secrets
  **Pin fix:** ` "args": ["-y", "@anthropic/mcp-browser@<exact-version>"] `
- **github** in `example-org/payments` (`.cursor/mcp.json`) — secrets
  **Pin fix:** ` "args": ["mcp-server-github@<exact-version>"] `

- **Product:** auctelis 0.1.11
- **Unpinned MCP launchers:** 2

### Repositories (ranked by tier-2 reach)

| Repository | Reach | tier2 | tier1 | tier0 | Unpinned | Watch |
| --- | --- | --- | --- | --- | --- | --- |
| `example-org/frontend` | 2 | 1 | 1 | 0 | 1 | [Watch PRs in example-org/frontend](https://github.com/example-org/frontend/new/main?filename=.github%2Fworkflows%2Fauctelis.yml&value=%23+Lockless+Authority+Diff+%E2%80%94+write+with+%60auctelis+init+--lockless%60+%28no+lock+required%29.%0A%23+Comment-only%3A+PRs+with+authority+changes+get+the+reach+diff+%28quiet+on+NONE%29.%0A%23+Add+locked%3A+%22true%22+later+to+enforce%2C+or+comment-on-none%3A+%22true%22+for+every+PR.%0Aname%3A+auctelis%0Aon%3A+%5Bpull_request%5D%0Apermissions%3A+%7B+contents%3A+read%2C+pull-requests%3A+write+%7D%0Ajobs%3A%0A++diff%3A%0A++++runs-on%3A+ubuntu-latest%0A++++steps%3A%0A++++++-+uses%3A+actions%2Fcheckout%403d3c42e5aac5ba805825da76410c181273ba90b1+%23+v7.0.1%0A++++++-+uses%3A+roham-amd%2Fauctelis%40v0.1.11%0A++++++++with%3A+%7B+locked%3A+%22false%22+%7D%0A&message=Add+auctelis+lockless+PR+Watch+workflow) |
| `example-org/payments` | 1 | 1 | 0 | 0 | 1 | [Watch PRs in example-org/payments](https://github.com/example-org/payments/new/main?filename=.github%2Fworkflows%2Fauctelis.yml&value=%23+Lockless+Authority+Diff+%E2%80%94+write+with+%60auctelis+init+--lockless%60+%28no+lock+required%29.%0A%23+Comment-only%3A+PRs+with+authority+changes+get+the+reach+diff+%28quiet+on+NONE%29.%0A%23+Add+locked%3A+%22true%22+later+to+enforce%2C+or+comment-on-none%3A+%22true%22+for+every+PR.%0Aname%3A+auctelis%0Aon%3A+%5Bpull_request%5D%0Apermissions%3A+%7B+contents%3A+read%2C+pull-requests%3A+write+%7D%0Ajobs%3A%0A++diff%3A%0A++++runs-on%3A+ubuntu-latest%0A++++steps%3A%0A++++++-+uses%3A+actions%2Fcheckout%403d3c42e5aac5ba805825da76410c181273ba90b1+%23+v7.0.1%0A++++++-+uses%3A+roham-amd%2Fauctelis%40v0.1.11%0A++++++++with%3A+%7B+locked%3A+%22false%22+%7D%0A&message=Add+auctelis+lockless+PR+Watch+workflow) |
| `example-org/docs` | 1 | 0 | 1 | 0 | 0 | **Watching** `example-org/docs` |

## Tier-2 reach by repository

### `example-org/frontend`

[Watch PRs in example-org/frontend](https://github.com/example-org/frontend/new/main?filename=.github%2Fworkflows%2Fauctelis.yml&value=%23+Lockless+Authority+Diff+%E2%80%94+write+with+%60auctelis+init+--lockless%60+%28no+lock+required%29.%0A%23+Comment-only%3A+PRs+with+authority+changes+get+the+reach+diff+%28quiet+on+NONE%29.%0A%23+Add+locked%3A+%22true%22+later+to+enforce%2C+or+comment-on-none%3A+%22true%22+for+every+PR.%0Aname%3A+auctelis%0Aon%3A+%5Bpull_request%5D%0Apermissions%3A+%7B+contents%3A+read%2C+pull-requests%3A+write+%7D%0Ajobs%3A%0A++diff%3A%0A++++runs-on%3A+ubuntu-latest%0A++++steps%3A%0A++++++-+uses%3A+actions%2Fcheckout%403d3c42e5aac5ba805825da76410c181273ba90b1+%23+v7.0.1%0A++++++-+uses%3A+roham-amd%2Fauctelis%40v0.1.11%0A++++++++with%3A+%7B+locked%3A+%22false%22+%7D%0A&message=Add+auctelis+lockless+PR+Watch+workflow)

- **browser** (`.cursor/mcp.json`) — secrets

### `example-org/payments`

[Watch PRs in example-org/payments](https://github.com/example-org/payments/new/main?filename=.github%2Fworkflows%2Fauctelis.yml&value=%23+Lockless+Authority+Diff+%E2%80%94+write+with+%60auctelis+init+--lockless%60+%28no+lock+required%29.%0A%23+Comment-only%3A+PRs+with+authority+changes+get+the+reach+diff+%28quiet+on+NONE%29.%0A%23+Add+locked%3A+%22true%22+later+to+enforce%2C+or+comment-on-none%3A+%22true%22+for+every+PR.%0Aname%3A+auctelis%0Aon%3A+%5Bpull_request%5D%0Apermissions%3A+%7B+contents%3A+read%2C+pull-requests%3A+write+%7D%0Ajobs%3A%0A++diff%3A%0A++++runs-on%3A+ubuntu-latest%0A++++steps%3A%0A++++++-+uses%3A+actions%2Fcheckout%403d3c42e5aac5ba805825da76410c181273ba90b1+%23+v7.0.1%0A++++++-+uses%3A+roham-amd%2Fauctelis%40v0.1.11%0A++++++++with%3A+%7B+locked%3A+%22false%22+%7D%0A&message=Add+auctelis+lockless+PR+Watch+workflow)

- **github** (`.cursor/mcp.json`) — secrets

### `example-org/docs`

**Watching** `example-org/docs`

_No tier-2 records._

## Unpinned MCP launchers

### `example-org/frontend`

- `browser` (`.cursor/mcp.json`) — pin the package: npx -y @anthropic/mcp-browser@&lt;exact-version&gt; **Pin fix:** ` "args": ["-y", "@anthropic/mcp-browser@<exact-version>"] `

### `example-org/payments`

- `github` (`.cursor/mcp.json`) — pin the package: uvx mcp-server-github@&lt;exact-version&gt; **Pin fix:** ` "args": ["mcp-server-github@<exact-version>"] `

## Coverage and limits

### Honesty

This report describes DECLARED/CONFIGURED agent authority observed by a passive scan. It is not a safety certificate, does not prove EFFECTIVE permissions, and does not establish VERIFIED runtime behavior.

- No walk truncation reported for this scan.
- Inventory is DECLARED/CONFIGURED only.

### Not auto-inspected

- Browser agents (MANUAL_ONLY)
- Memory / RAG (MANUAL_ONLY)
- Model providers (MANUAL_ONLY)
- Multimodal artifacts (MANUAL_ONLY)
- Runtime behavior (UNSUPPORTED)
- Publisher / artifact provenance (MANUAL_ONLY)

These families have no passive discovery adapter; they require manual review.

## Lockless PR Watch workflow

Copy into `.github/workflows/auctelis.yml` (or use **Watch PRs** when linked):

```yaml
# Lockless Authority Diff — write with `auctelis init --lockless` (no lock required).
# Comment-only: PRs with authority changes get the reach diff (quiet on NONE).
# Add locked: "true" later to enforce, or comment-on-none: "true" for every PR.
name: auctelis
on: [pull_request]
permissions: { contents: read, pull-requests: write }
jobs:
  diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: roham-amd/auctelis@v0.1.11
        with: { locked: "false" }
```

_Next step: paste the lockless workflow below (or click **Watch PRs** per repo) to watch future agent-authority changes in one quiet PR comment._
