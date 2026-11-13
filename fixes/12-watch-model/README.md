# 12. Watch model

## I noticed
According to the `tools/list` descriptions, a Reddit watch searches "optionally inside one subreddit", a daily watch runs "for 7 days after the first run", a plan has a limit on active watches (mine was 3), and `pond_watch_extend` adds 7 days and has to be called by hand. My digest covers 4 subreddits plus Hacker News, so it needs 5 watches. That is more than the cap, and every one of them stops after a week unless someone extends it.

## Fix
`watches.py`:
- a watch holds a list of sources (scraper, query, optional subreddit), 1 to 10 of them, with duplicates removed;
- the active-watch limit counts watches, not sources;
- one daily run fans out to every source;
- a watch linked to a workflow renews itself on each tick while that workflow is live. Once the workflow is paused or archived, the watch runs out its current 7-day window and expires.

## Metric
- Watches needed for the digest: 5 today (over the cap of 3) -> 1 (`test_digest_needs_five_watches_today_and_one_with_sources`).
- Manual extend calls per year to keep it running: 5 watches x 52 = 260 today -> 0 (formula: 365 / 7 rounded down = 52 extends per watch per year).

Run: `uv run pytest -q fixes/12-watch-model`
Effort: M (estimate).
