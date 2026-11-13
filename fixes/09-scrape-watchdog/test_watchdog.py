import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from watchdog import Watchdog, minutes_saved


class FakeClock:
    def __init__(self):
        self.t = datetime(2026, 11, 12, 22, 51, 9)

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


def make(stall=timedelta(minutes=5)):
    clock, cancelled = FakeClock(), []
    return (
        clock,
        cancelled,
        Watchdog(clock=clock, stall_after=stall, cancel_worker=cancelled.append),
    )


def test_run_fails_at_budget_with_reason_and_progress():
    clock, cancelled, wd = make(stall=timedelta(hours=1))
    wd.start("sr_1", "sw_1")
    clock.advance(minutes=3)
    wd.progress("sr_1", items_found=4, pages_done=2)
    clock.advance(minutes=6, seconds=59)
    assert wd.status("sr_1")["status"] == "running"
    clock.advance(seconds=1)
    v = wd.status("sr_1")
    assert v["status"] == "failed" and v["failure_reason"] == "timeout"
    assert v["progress"]["items_found"] == 4 and "4 items" in v["failure_detail"]
    assert v["elapsed_s"] == 600 and cancelled == ["sr_1"]


def test_observed_run_would_have_ended_at_10_min_not_20m16s():
    clock, _, wd = make(stall=timedelta(hours=1))
    wd.start("sr_8eb5", "sw_cbdee")
    clock.advance(minutes=20, seconds=16)
    v = wd.status("sr_8eb5")
    assert v["status"] == "failed" and v["elapsed_s"] == 600


def test_stall_detected_before_budget():
    clock, _, wd = make()
    wd.start("sr_1", "sw_1")
    clock.advance(minutes=5)
    assert wd.tick() == ["sr_1"]
    assert wd.runs["sr_1"].failure_reason == "stalled"


def test_progress_resets_stall_timer():
    clock, _, wd = make()
    wd.start("sr_1", "sw_1")
    for i in range(1, 4):
        clock.advance(minutes=3)
        wd.progress("sr_1", items_found=i, pages_done=i)
        assert wd.tick() == []


def test_stop_watch_cancels_in_flight_run():
    _clock, cancelled, wd = make()
    wd.start("sr_1", "sw_1")
    wd.start("sr_2", "sw_2")
    assert wd.stop_watch("sw_1") == ["sr_1"]
    assert (
        wd.runs["sr_1"].status == "cancelled"
        and wd.runs["sr_1"].failure_reason == "watch_stopped"
    )
    assert wd.runs["sr_2"].status == "running" and cancelled == ["sr_1"]


def test_success_is_final():
    clock, _, wd = make()
    wd.start("sr_1", "sw_1")
    wd.succeed("sr_1")
    clock.advance(hours=1)
    assert wd.tick() == [] and wd.status("sr_1")["failure_reason"] is None


def test_minutes_saved_formula():
    assert (
        round(
            minutes_saved(timedelta(minutes=20, seconds=16), timedelta(minutes=10)), 2
        )
        == 10.27
    )
    assert minutes_saved(timedelta(minutes=5), timedelta(minutes=10)) == 0
