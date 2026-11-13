"""Add up the impact numbers from each fix's results file into bench/impact.json.
Every figure here is read from a results file or computed by the formula next to it.

run: uv run python bench/impact.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def main() -> None:
    diet = load("fixes/05-tool-list-diet/results.json")
    export = load("fixes/06-export-by-url/results.json")
    landing = load("fixes/07-landing-weight/results.json")
    search = load("fixes/02-catalog-search/results.json")["summary"]
    bench = load("bench/results.json")
    observed_s, budget_s = 20 * 60 + 16, 10 * 60
    out = {
        "per_session_tokens_saved_descriptions": {
            "value": diet["estimated_tokens_before"] - diet["estimated_tokens_after_descriptions"],
            "formula": "(tools/list compact chars before - after moving description text to a skill) / 4",
            "source": "fixes/05-tool-list-diet/results.json",
        },
        "per_session_tokens_saved_with_output_schema": {
            "value": diet["estimated_tokens_before"] - diet["estimated_tokens_after_both"],
            "formula": "same, also dropping outputSchema; counts only for clients that put outputSchema in context",
            "source": "fixes/05-tool-list-diet/results.json",
        },
        "per_workflow_build_tokens_saved": {
            "value": export["estimated_tokens_saved_per_export"] * export["exports_per_build_observed"],
            "formula": "(export response bytes today - with signed URL) / 4 x 1 export per build (observed)",
            "source": "fixes/06-export-by-url/results.json",
        },
        "landing_first_load_bytes_saved_gzip": {
            "value": landing["posthog_chunks_on_landing"]["gzip"],
            "formula": "gzip -9 size of the PostHog chunk, moved off the first load",
            "source": "fixes/07-landing-weight/results.json",
        },
        "landing_bytes_saved_by_brotli": {
            "value": (landing["landing_total_js"]["gzip"] + landing["landing_total_css"]["gzip"])
            - (landing["landing_total_js"]["brotli"] + landing["landing_total_css"]["brotli"]),
            "formula": "landing JS+CSS gzip -9 minus brotli -q11, both computed locally",
            "source": "fixes/07-landing-weight/results.json",
        },
        "search_top3_rate": {
            "before": search["live"]["rate"],
            "after": search["bm25"]["rate"],
            "zero_result_queries_before": search["live_zero_results"],
            "source": "fixes/02-catalog-search/results.json (20 queries)",
        },
        "minutes_saved_per_stuck_run": {
            "value": round((observed_s - budget_s) / 60, 2),
            "formula": "(20 min 16 s observed - 10 min budget) / 60",
            "source": "observation 2026-11-12; formula in fixes/09-scrape-watchdog/watchdog.py",
        },
        "tools_list_wire_bytes": {
            "identity": bench["tools_list"]["by_accept_encoding"]["identity"]["wire_bytes"],
            "gzip": bench["tools_list"]["by_accept_encoding"]["gzip"]["wire_bytes"],
            "source": "bench/results.json",
        },
    }
    (ROOT / "bench" / "impact.json").write_text(json.dumps(out, indent=2) + "\n")
    for k, v in out.items():
        print(k, {kk: vv for kk, vv in v.items() if kk not in ("formula", "source")})


if __name__ == "__main__":
    main()
