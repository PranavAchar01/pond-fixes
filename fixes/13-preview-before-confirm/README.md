# 13. Preview before confirm

## I noticed
Pond let me confirm my workflow 2 min 53 s after I sent the brief, and the app showed it as Running. None of its sources had returned anything yet. The first proof came from the first test run, 16 min 30 s later: `failed`, 0 posts, "Reddit watch run still in progress after 16 minutes; web search found 2 posts, none in scope. Empty digest delivered." (`data/build-session/report.json`). The four searches behind that step took 1.2 s, 1.1 s, 0.2 s and 2.1 s (`ws_*.out`). Three came back empty and one returned 2 job-hunting posts from outside my four subreddits. All of that could be known in under 5 seconds, before confirm.

## Fix
`preview.py` runs every source step once on a small sample while the workflow is still a draft. Each source gets one query, a short window, a hard budget, and the workflow's own scope check. Each step gets a verdict: `ok`, `empty`, `out_of_scope` or `timeout`, with a sample and the reason items were dropped. The canvas can put that on the node ("0 of 2 in scope: outside your 4 subreddits"). `confirm()` refuses a draft whose preview kept nothing, unless the member gives a reason, and that reason is stored on the workflow.

## Metric
Time from brief to knowing the workflow delivers nothing: 1,180 s (19 min 40 s) -> 177.6 s (2 min 58 s), 85% less. Formula: confirm time plus the captured search times, against the time the failed report arrived. One observed build. `replay.py` replays my build through `preview()` and writes `results.json`.

Run: `uv run pytest -q fixes/13-preview-before-confirm && uv run python fixes/13-preview-before-confirm/replay.py`
Effort: M (estimate).
