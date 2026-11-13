# DONE

Builder report for pond-fixes, 2026-11-12 (local time; files carry UTC timestamps from 2026-11-13).

## What was built
- `tools/pond_client.py`: MCP client. Reads POND_API_KEY from the environment, then the keychain (service pond-api-key). Importable, never prints the key.
- `bench/measure.py` -> `bench/results.json`; `bench/impact.py` -> `bench/impact.json`.
- `fixes/02` to `fixes/12`, each with README (I noticed / Fix / Metric), code and tests. Fix 01 lives in `bench/`.
- 55 pytest tests pass (`uv run pytest -q`), including two that run the Node tests for `worker.ts` and `lazy-track.ts`. `ruff check` is clean.

## Every metric and its source
| Metric | Value | Source |
|---|---|---|
| p50 / p95 ms, N=15, 1 s spacing | current_user 219.1/516.4, catalog_search 196.3/333.2, capabilities 159.2/301.4, tools/list 367.1/1124.9, recent_updates 212.0/281.4 | bench/results.json (00:17 to 00:19 UTC) |
| tools/list wire bytes | 359,514 identity, 46,801 gzip, br not served | bench/results.json |
| tools/list est. tokens | 89,698 (chars / 4, labeled estimate) | bench/results.json |
| Mcp-Session-Id on initialize | not returned | bench/results.json |
| pond_recent_updates items | 0 on all 15 calls | bench/results.json |
| Catalog top-3 hit rate | live 7/20, BM25 19/20, live zero-result 13 | fixes/02-catalog-search/results.json |
| Validator | 4 errors in 4 items, 39 warnings in 11 items | validate_catalog.py on data/ |
| Validation errors | server vs fix for 4 cases | fixes/04-validation-errors/live_errors.json |
| Tool-list diet | 358,793 -> 334,094 -> 125,637 chars | fixes/05-tool-list-diet/results.json |
| Export | 140,226 -> 7,510 bytes | fixes/06-export-by-url/results.json |
| Landing | 88 JS files, 473,459 gzip; PostHog 92,065 gzip; wallet on landing 0 | fixes/07-landing-weight/results.json |
| Landing headers and video sizes | gzip only, immutable assets, webm 6,489,523 | fixes/07-landing-weight/headers.json |
| Soft 404 | 8 of 8 paths answer 200 | fixes/08-soft-404/results.json |
| Stuck run | 10.27 min saved (formula) | brief observation 20 min 16 s; list_runs.out shows over 16 min |
| Feed backfill | 0 -> 21 entries | fixes/10 test on data/catalog.txt |
| Confirm | 2 stale fields in confirm.out | fixes/11 test |
| Watches | 5 -> 1; 260 -> 0 extends/yr (formula) | fixes/12 test and README |

## What I could not measure, and why
- Wallet chunks on the landing page: the brief expected them there, but the static import graph shows they are not on the `/` route. I reported that instead of a saving. I ran no browser (rule: no page tests), so a runtime-only import is not ruled out.
- Sizes of the below-fold step and guarantee videos: their file names are built at runtime and were not in the mirror.
- Whether clients put outputSchema into model context: not checked, so the outputSchema token saving is labeled conditional.
- Retries saved by better validation errors: would need many agent runs.
- The 20 min 16 s scrape duration comes from the brief. The captured files only show the run still going after 16 minutes. I made no pond_scrape_* calls (not free).
- Web search OR and quotes, charged_usd estimates, contradictory authoring docs: listed in the README as not built. They were not in the build list and I had no clean before data.
- The 386 KB tools/list figure in the brief matches `json.dumps` with ASCII escaping (386,073 chars in the first bench run). The raw response is 359,514 bytes, and that is the number I used.

## Notes
- data/ holds captured Pond responses with no user data (no email). `pond_current_user` bodies are never stored.
- The site mirror is read from the scratchpad path and is not copied into the repo.
