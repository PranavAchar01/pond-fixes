# 09. Scrape watchdog

## I noticed
My Reddit watch run `sr_8eb5d2b2596dd95c4fa8c3a3` began at 22:51:09 UTC with a 10-minute budget. It still said `running` long after that. The workflow run that waited on it wrote "Reddit watch run still in progress after 16 minutes" (`list_runs.out`). By my own timing it ran 20 min 16 s and then failed with no reason given. The status response has no progress field, so a caller can't tell slow from stuck.

## Fix
`watchdog.py` is a reference run watchdog with an injected clock:
- a run past its budget is marked `failed` with `failure_reason: "timeout"`, its last progress, and the deadline as the end time, and its worker is cancelled;
- a run whose progress has not moved for 5 minutes fails as `stalled`;
- stopping a watch cancels its run in flight (`watch_stopped`);
- every status read enforces the budget first, and returns `progress` (items_found, pages_done, last_progress_at), `elapsed_s`, `budget_s` and `failure_reason`.

## Metric
Minutes a caller stops waiting earlier on a stuck run: (20 min 16 s observed - 10 min budget) = 10.27 min per stuck run (formula; one observed run). The test `test_observed_run_would_have_ended_at_10_min_not_20m16s` replays this case on a fake clock.

Run: `uv run pytest -q fixes/09-scrape-watchdog`
Effort: M (estimate).
