# 08. Soft 404

## I noticed
Every path I tried returns HTTP 200 with the same 9,350-byte SPA shell: `/docs`, `/pricing`, `/catalog`, `/help`, `/marketplace`, `/changelog`, `/status` and a made-up path (`results.json`, 2026-11-13). Crawlers index these as real pages, uptime monitors see them as up, and an agent that fetches `/docs` gets a blank app shell and assumes the docs exist.

## Fix
Two options for a Vite SPA on Cloudflare:
1. Recommended: `worker.ts` runs before static assets (`run_worker_first = true`, `not_found_handling = "none"` in `wrangler.toml`). It checks the path against `routes.json`, the 56 real routes taken from the built bundle by `extract_routes.py`, which CI runs after `vite build`. A known route gets `index.html` with 200. An unknown path gets the same shell with 404, so the app still shows its own not-found page. Static files and `/mcp`, `/api/`, `/auth/` pass straight through.
2. Smaller: if `/docs`, `/pricing` and the others should exist, add redirects to real pages and keep the SPA fallback for everything else. Unknown paths stay at 200 this way, so option 1 is still needed for those.

## Metric
Missing paths that answer 200: 8 of 8 today, 0 of 8 with the Worker (`worker.test.ts`). After a deploy, `check_404.py --expect-404` works as a CI or uptime check.

Run: `uv run python fixes/08-soft-404/check_404.py`, `node --test fixes/08-soft-404/worker.test.ts`
Effort: S (estimate).
