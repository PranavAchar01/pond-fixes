# Pond fixes

I spent 2026-11-12 building a workflow on Pond through the MCP server, and wrote down the backend issues I hit. Each one has a runnable fix here with a before and after number. I measured the numbers against the live server, the live site, or data I captured during that build. Where a number is an estimate, the formula is next to it. All tests run offline. The live scripts make only free, read-only calls.

## Summary

| # | Fix | What changes | Metric before -> after | Effort (estimate) |
|---|---|---|---|---|
| 01 | [Measure first](bench/README.md) | Baseline for free MCP calls | p50 159 to 367 ms; tools/list 359,514 bytes; no Mcp-Session-Id | S |
| 02 | [Catalog search](fixes/02-catalog-search/README.md) | BM25 ranking replaces strict matching | top-3 hit rate 35% -> 95% (20 queries); empty results 13 -> 0 | S |
| 03 | [Publish validator](fixes/03-publish-validator/README.md) | CI check on capabilities and platform | 4 broken live items -> blocked at publish | S |
| 04 | [Validation errors](fixes/04-validation-errors/README.md) | `{path, message}` with the field name and range | errors naming field and range: 0 of 4 -> 4 of 4 | S |
| 05 | [Tool-list diet](fixes/05-tool-list-diet/README.md) | Procedures move to a skill; outputSchema on request | 89,698 -> 83,523 est. tokens (31,409 with outputSchema dropped) | M |
| 06 | [Export by URL](fixes/06-export-by-url/README.md) | Signed URL instead of inline base64 | 140,226 -> 7,510 bytes per export | S |
| 07 | [Landing weight](fixes/07-landing-weight/README.md) | Lazy PostHog, brotli, lazy videos | first-load JS gzip 473,459 -> 381,394 bytes | S to M |
| 08 | [Soft 404](fixes/08-soft-404/README.md) | Worker returns 404 for unknown paths | missing paths answering 200: 8 of 8 -> 0 of 8 | S |
| 09 | [Scrape watchdog](fixes/09-scrape-watchdog/README.md) | Budget, progress, failure reason, cancel | stuck run 20 min 16 s -> fails at 10 min with a reason | M |
| 10 | [Updates feed hook](fixes/10-updates-feed/README.md) | Publishing writes a feed entry atomically | feed entries 0 -> 21 | S |
| 11 | [Confirm transaction](fixes/11-confirm-transaction/README.md) | One-UPDATE confirm with a revision guard | stale fields after confirm 2 -> 0 | S |
| 12 | [Watch model](fixes/12-watch-model/README.md) | Multi-source watches, kept alive while live | watches for my digest 5 -> 1; manual extends 260/yr -> 0 | M |
| 13 | [Preview before confirm](fixes/13-preview-before-confirm/README.md) | Every source runs once on a sample before confirm; confirm needs a result or a reason | brief to first verdict 19 min 40 s -> 2 min 58 s | M |

## Total impact

With every fix applied to the build I did (`bench/session.json`, built by `bench/session_total.py`):

- Time from sending the brief to knowing whether the workflow works: 19 min 40 s -> 2 min 58 s, 85% less (fix 13; one observed build).
- Data an agent loads to build and check one workflow: 581,242 -> 388,395 bytes, 33% less. For clients that also load outputSchema: 179,938 bytes, 69% less. About 145,000 -> 97,000 tokens (ESTIMATE: bytes / 4). This counts the tools/list result plus every response body in my build, with fixes 05 and 06 applied, and fix 06's signed URL also used for `pond_workflow_get`.

Per fix, from `bench/impact.json`, which `bench/impact.py` builds from each fix's results file:

- Tokens saved per session: about 6,175 for every client, from moving description procedures into a skill. Up to about 58,289 for clients that also load outputSchema. ESTIMATE: tools/list compact JSON chars / 4, before minus after.
- Tokens saved per workflow build: about 33,179 per export (ESTIMATE: bytes / 4; base64 likely tokenizes worse). My build exported once.
- Landing bytes saved: 92,065 bytes gzip off the first load by deferring PostHog, measured on the mirror files. Brotli would save about 73,557 more on the landing JS and CSS (ESTIMATE: computed locally at gzip -9 and brotli -q11).
- Search success: top-3 hit rate 35% -> 95% on 20 queries, with 13 empty results -> 0.
- Minutes saved per stuck run: 10.27 (formula: 20 min 16 s observed minus the 10 min budget; one observed run).

## How to run

```sh
uv sync
uv run pytest -q                                   # all tests, offline
export POND_API_KEY=...                            # or keep it in the macOS keychain, service pond-api-key
uv run python bench/measure.py                     # live latency and sizes (free calls only)
uv run python fixes/02-catalog-search/evaluate.py  # live search vs BM25 (20 free calls)
uv run python fixes/04-validation-errors/capture_live.py
uv run python fixes/03-publish-validator/validate_catalog.py
uv run python fixes/05-tool-list-diet/diet.py
uv run python fixes/06-export-by-url/export_shape.py
uv run python fixes/07-landing-weight/head_check.py
uv run python fixes/08-soft-404/check_404.py
uv run python bench/impact.py
uv run python fixes/13-preview-before-confirm/replay.py
uv run python bench/session_total.py
```

`tools/pond_client.py` is a small MCP client. It reads `POND_API_KEY` from the environment first and falls back to the keychain. The key is never printed or written to disk. The TypeScript pieces (`worker.ts`, `lazy-track.ts`) need Node 23.6 or newer to run their tests. pytest runs them when `node` is on the PATH.

## Also noticed, not built here

- Web search seemed to ignore OR and quoted phrases. Several of my searches came back empty with "Try different words or fewer filters." The captured outputs do not include the queries I sent, so I have no clean before and after for it.
- `charged_usd` is reported after a call, with no estimate beforehand.
- The authoring docs disagree with each other in places.
