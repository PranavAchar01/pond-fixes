import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


pv = _load("preview")
replay = _load("replay")


def fixed(items, seconds=0.5, timed_out=False):
    return lambda src: pv.Fetched(items, seconds, timed_out)


def test_step_verdicts():
    keep = lambda it: (it.source == "r/python", "outside scope")
    a = pv.preview([pv.Source("s", "q")], fixed([]), keep).steps[0]
    b = pv.preview(
        [pv.Source("s", "q")], fixed([pv.Item("t", "u", "r/jobs")]), keep
    ).steps[0]
    c = pv.preview(
        [pv.Source("s", "q")], fixed([pv.Item("t", "u", "r/python")]), keep
    ).steps[0]
    d = pv.preview([pv.Source("s", "q")], fixed([], timed_out=True), keep).steps[0]
    assert (a.status, b.status, c.status, d.status) == (
        "empty",
        "out_of_scope",
        "ok",
        "timeout",
    )
    assert b.why == ["outside scope"]


def test_confirm_needs_a_passing_preview():
    empty = pv.preview([pv.Source("s", "q")], fixed([]), lambda it: (True, ""))
    with pytest.raises(pv.NeedsPreview):
        pv.confirm({"id": "w"}, None)
    with pytest.raises(pv.NeedsPreview):
        pv.confirm({"id": "w"}, empty)
    forced = pv.confirm(
        {"id": "w"}, empty, force_reason="new subreddit, expect posts next week"
    )
    assert (
        forced["confirmed_without_results"] == "new subreddit, expect posts next week"
    )
    good = pv.preview(
        [pv.Source("s", "q")],
        fixed([pv.Item("t", "u", "r/python")]),
        lambda it: (True, ""),
    )
    assert pv.confirm({"id": "w"}, good)["status"] == "confirmed"


def test_replay_of_my_build_blocks_confirm_in_seconds_not_minutes():
    out = replay.run()
    assert out["with_preview"]["ready"] is False
    assert out["with_preview"]["verdict"] == "0 in scope of 2 found across 4 sources"
    assert out["with_preview"]["preview_seconds_sequential"] == pytest.approx(4.6)
    assert out["brief_to_first_verdict_s"] == {"before": 1180, "after": 177.6}
    assert out["reduction"] == pytest.approx(0.849, abs=0.001)
