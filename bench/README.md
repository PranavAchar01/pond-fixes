# 01. Measure first

## I noticed
I had no baseline for the MCP server, so every other fix needed one.

## Fix
`bench/measure.py` makes only free, read-only calls: `pond_current_user`, `pas_catalog_search`, `pas_capabilities`, `tools/list` and `pond_recent_updates`. Each one runs 15 times in a row with 1 s between calls. It stores latency and sizes only. No response bodies are kept, because `pond_current_user` returns the member's email.

## Metric (bench/results.json, run 2026-11-13 00:17 UTC)

| Call | N | p50 ms | p95 ms |
|---|---|---|---|
| pond_current_user | 15 | 219.1 | 516.4 |
| pas_catalog_search | 15 | 196.3 | 333.2 |
| pas_capabilities | 15 | 159.2 | 301.4 |
| tools/list | 15 | 367.1 | 1124.9 |
| pond_recent_updates | 15 | 212.0 | 281.4 |

p95 is nearest-rank, so with N=15 it equals the slowest call. Each call opens a new TLS connection (urllib), which adds to every number above.

- `tools/list`: 89 tools, 359,514 bytes on the wire with no Accept-Encoding. With `Accept-Encoding: gzip` the server answers gzip at 46,801 bytes. With `Accept-Encoding: br` it sends identity (no brotli).
- Estimated tokens for the tools/list result: 89,698 (ESTIMATE: compact JSON chars / 4). Of the 358,793 compact chars, outputSchema is 207,161, inputSchema 83,814, descriptions 51,451.
- `initialize` returns no `Mcp-Session-Id` header, so the server is stateless and every client sends the whole tool list again each session.
- `pond_recent_updates` returned `{"updates":[],"next_cursor":null}` on all 15 calls.

Run: `uv run python bench/measure.py`
