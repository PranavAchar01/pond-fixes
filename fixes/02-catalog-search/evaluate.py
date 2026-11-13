"""Top-3 success rate on 20 member queries: live pas_catalog_search vs the BM25 fix.

run: uv run python fixes/02-catalog-search/evaluate.py [--offline]
--offline skips the live server and scores only the ranker.
Writes fixes/02-catalog-search/results.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from ranker import Ranker

from fixes.common.data import catalog_items

QUERIES = json.loads((HERE / "queries.json").read_text())


def hit(ids: list[str], relevant: list[str], k: int = 3) -> bool:
    return any(i in relevant for i in ids[:k])


def live_ids(client, query: str) -> tuple[list[str], str | None]:
    r = client.call(
        "pas_catalog_search", {"requestId": "eval", "query": query, "limit": 3}
    )
    text = client.text(r)
    try:
        items = json.loads(text)["data"]["items"]
        return [i["locator"]["solutionId"] for i in items], None
    except (json.JSONDecodeError, KeyError, TypeError):
        return [], text[:200]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    items = catalog_items()
    plain, syn = Ranker(items), Ranker(items, use_synonyms=True)
    client = None
    if not args.offline:
        from tools.pond_client import PondClient

        client = PondClient()
        client.initialize()
    rows = []
    for q in QUERIES:
        row = {
            "query": q["q"],
            "relevant": q["relevant"],
            "bm25": [i["locator"]["solutionId"] for i in plain.search(q["q"], 3)],
            "bm25_synonyms": [
                i["locator"]["solutionId"] for i in syn.search(q["q"], 3)
            ],
        }
        if client:
            row["live"], row["live_error"] = live_ids(client, q["q"])
            time.sleep(1)
        rows.append(row)
    n = len(rows)
    summary = {"n_queries": n, "k": 3}
    for key in ("live", "bm25", "bm25_synonyms"):
        if key in rows[0]:
            hits = sum(hit(r[key], r["relevant"]) for r in rows)
            summary[key] = {"hits": hits, "rate": round(hits / n, 3)}
    if client:
        summary["live_zero_results"] = sum(1 for r in rows if not r["live"])
    out = {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": summary,
        "rows": rows,
    }
    (HERE / "results.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
