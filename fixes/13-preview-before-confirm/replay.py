"""Replay my 2026-11-12 build through preview() using the searches captured during it, and write
results.json with the time it took to learn the workflow delivers nothing, today and with preview."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data" / "build-session"

import importlib.util

spec = importlib.util.spec_from_file_location("preview", HERE / "preview.py")
pv_mod = importlib.util.module_from_spec(spec)
sys.modules["preview"] = pv_mod
spec.loader.exec_module(pv_mod)

SUBREDDITS = {"r/statistics", "r/learnpython", "r/datascience", "r/python"}
# The four searches I ran during the build, in order. The captured files hold the responses and
# their timing; the step each one fed is from the workflow graph (read-posts).
SEARCHES = [
    ("read-posts:reddit", "ws_reddit.out"),
    ("read-posts:hn", "ws_hn.out"),
    ("read-posts:reddit-2", "ws_r2.out"),
    ("read-posts:hn-2", "ws_h2.out"),
]


def load(name: str) -> tuple[float, dict]:
    head, body = (DATA / name).read_text().split("\n", 1)
    return float(re.search(r"([\d.]+)s", head).group(1)), json.loads(body)


def fetch_captured(src):
    seconds, body = load(dict(SEARCHES)[src.step_id])
    items = []
    for r in body.get("results", []):
        m = re.search(r"reddit\.com/(r/[^/]+)", r["url"])
        items.append(pv_mod.Item(r["title"], r["url"], m.group(1) if m else "web"))
    return pv_mod.Fetched(items, seconds)


def in_scope(item):
    if item.source.lower() not in SUBREDDITS and "news.ycombinator.com" not in item.url:
        return False, f"outside the four subreddits ({item.source})"
    return True, ""


def run() -> dict:
    sources = [pv_mod.Source(step, step) for step, _ in SEARCHES]
    pv = pv_mod.preview(sources, fetch_captured, in_scope)
    tl = json.loads((DATA / "timeline.json").read_text())["events"]
    report = json.loads((DATA / "report.json").read_text())
    before = tl["report"]
    after_seq = tl["confirm"] + pv.seconds
    return {
        "source": "data/build-session (my build on 2026-11-12): timeline.json, ws_*.out, report.json",
        "today": {
            "confirmed_at_s": tl["confirm"],
            "first_verdict_at_s": before,
            "first_verdict": f"{report['status']}, {report['results']} {report['result_noun']}: {report['note']}",
            "minutes_from_confirm_to_verdict": round((before - tl["confirm"]) / 60, 2),
        },
        "with_preview": {
            "preview_seconds_sequential": pv.seconds,
            "preview_seconds_parallel": pv.seconds_parallel,
            "verdict_at_s_sequential": round(after_seq, 1),
            "verdict": pv.summary,
            "ready": pv.ready,
            "steps": [
                {
                    "step": s.step_id,
                    "status": s.status,
                    "found": s.found,
                    "in_scope": s.in_scope,
                    "seconds": s.seconds,
                    "why": s.why,
                }
                for s in pv.steps
            ],
        },
        "brief_to_first_verdict_s": {"before": before, "after": round(after_seq, 1)},
        "reduction": round(1 - after_seq / before, 3),
        "formula": "after = confirm time (173 s) + sum of the captured search times; before = time the failed test report arrived",
    }


if __name__ == "__main__":
    out = run()
    (HERE / "results.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        json.dumps(out["brief_to_first_verdict_s"]),
        out["with_preview"]["verdict"],
        f"reduction {out['reduction']:.0%}",
    )
