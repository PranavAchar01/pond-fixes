# 10. Updates feed hook

## I noticed
`pond_recent_updates` returned an empty list on 15 of 15 calls (`bench/results.json`). Over the same period the catalog listed 21 published solutions, at least one published that day (`investor-match` 1.0.1, 2026-11-12 06:43 UTC).

## Fix
`feed.py` writes the version row and its `pas_update` entry in one transaction, so a published version always has an entry and a failed publish leaves neither. The entry title is "New: X" for a first version and "X updated to V" after that. `backfill()` creates entries for versions published before the hook and can run twice safely. `recent_updates()` keeps the current response shape (`updates`, `next_cursor`, `kinds` filter).

## Metric
Feed entries for the current catalog: 0 today -> 21 after backfill (`test_backfill_real_catalog_gives_21_entries_and_is_idempotent`, using the real catalog's `publishedAt`).

Run: `uv run pytest -q fixes/10-updates-feed`
Effort: S (estimate).
