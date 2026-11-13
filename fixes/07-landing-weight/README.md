# 07. Landing page weight

## I noticed
I went in expecting wallet code (Privy, WalletConnect, MoonPay, Farcaster) on the landing page. In the current build those chunks sit behind app routes, and the landing route never imports them. The heavy eager chunk is PostHog.

What the `/` route loads, from a mirror of the build plus live HEAD checks (`results.json`, `headers.json`, 2026-11-13):
- `index.html` lists 1 entry script and 72 modulepreloads. With the lazy landing chunk (`routes-PvcBNCWd.js`) and its static imports, that makes 88 JS files: 1,413,699 bytes raw, 473,459 gzip, plus 265,348 bytes of CSS (43,973 gzip).
- `track-DKHn3SyZ.js` (PostHog) is modulepreloaded on first load: 282,145 bytes raw, 92,065 gzip.
- Chunks named for wallet or onramp code on the landing route: 0 bytes. The only wallet strings in the entry are file names in the lazy-route table.
- Asking for `Accept-Encoding: br, gzip` got gzip back. `/assets/*` sends `cache-control: public, max-age=31536000, immutable`, which is right.
- Hero video: desktop webm 6,489,523 bytes, mobile mp4 1,837,884 bytes (HEAD content-length). Below-the-fold step and guarantee videos use `preload="auto"`. Their file names are built at runtime and were not in the mirror, so I could not size them.

## Fix
1. `lazy-track.ts`: `track()` keeps its API, queues events, and loads PostHog on idle or on the first pointer event. Tests: `lazy-track.test.ts`.
2. Turn on brotli for `/assets` at Cloudflare.
3. Use `preload="none"` with an IntersectionObserver for videos below the fold.

## Metric
- Deferring PostHog takes 92,065 bytes gzip (282,145 raw) off the first load: about 19% of the landing JS gzip bytes.
- Brotli on the landing JS and CSS: 517,432 -> 443,875 bytes, saving 73,557 (ESTIMATE: gzip -9 and brotli -q11 computed locally on the mirror files. Cloudflare's own levels will differ).
- Wallet code split: nothing to remove, already done.

Run: `uv run python fixes/07-landing-weight/analyze_landing.py MIRROR_DIR` and `uv run python fixes/07-landing-weight/head_check.py`
Effort: S for PostHog and brotli, M for the videos (estimate).
