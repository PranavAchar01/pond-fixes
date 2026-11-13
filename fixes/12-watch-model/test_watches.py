import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from watches import LimitError, Source, WatchService, watches_needed_today

DIGEST = [
    Source("reddit", "statsmodels OR quantile regression", s)
    for s in ("learnpython", "datascience", "statistics", "Python")
] + [Source("hackernews", "statsmodels OR quantile regression")]


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 12, 16, 0)

    def __call__(self):
        return self.t


def svc(live=()):
    c = Clock()
    return c, WatchService(clock=c, is_workflow_live=lambda wid: wid in live)


def test_digest_needs_five_watches_today_and_one_with_sources():
    assert watches_needed_today(DIGEST) == 5
    _, s = svc()
    w = s.start("sw_1", "pranav", DIGEST)
    assert len(w.sources) == 5 and len(s.active("pranav")) == 1


def test_one_daily_run_covers_every_source():
    _, s = svc()
    s.start("sw_1", "pranav", DIGEST)
    assert len(s.due_runs()) == 5


def test_limit_counts_watches_not_sources():
    _, s = svc()
    for i in range(3):
        s.start(f"sw_{i}", "pranav", DIGEST)
    with pytest.raises(LimitError):
        s.start("sw_x", "pranav", DIGEST[:1])


def test_live_workflow_keeps_watch_alive_past_seven_days():
    c, s = svc(live={"pw_1"})
    s.start("sw_1", "pranav", DIGEST, workflow_id="pw_1")
    for _ in range(30):
        c.t += timedelta(days=1)
        s.tick()
    assert s.watches["sw_1"].status == "active"
    assert s.watches["sw_1"].expires_at == c.t + timedelta(days=7)


def test_unlinked_watch_expires_after_seven_days():
    c, s = svc()
    s.start("sw_1", "pranav", DIGEST)
    c.t += timedelta(days=7)
    s.tick()
    assert s.watches["sw_1"].status == "expired"


def test_paused_workflow_lets_watch_run_out_its_window():
    live = {"pw_1"}
    c = Clock()
    s = WatchService(clock=c, is_workflow_live=lambda wid: wid in live)
    s.start("sw_1", "pranav", DIGEST, workflow_id="pw_1")
    c.t += timedelta(days=10)
    s.tick()
    live.clear()
    c.t += timedelta(days=6, hours=23)
    s.tick()
    assert s.watches["sw_1"].status == "active"
    c.t += timedelta(hours=1)
    s.tick()
    assert s.watches["sw_1"].status == "expired"


def test_source_count_bounds_and_dedupe():
    _, s = svc()
    with pytest.raises(ValueError):
        s.start("sw_1", "pranav", [])
    w = s.start("sw_2", "pranav", DIGEST + DIGEST)
    assert len(w.sources) == 5
