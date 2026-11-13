"""Hit paths on joinpond.ai with a plain GET and report the HTTP status.
A path with no page should answer 404; today they answer 200 with the SPA shell.

run: uv run python fixes/08-soft-404/check_404.py [--base URL] [--expect-404]
--expect-404 exits 1 if any listed path does not return 404 (CI mode).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

PATHS = [
    "/docs",
    "/pricing",
    "/catalog",
    "/help",
    "/marketplace",
    "/changelog",
    "/status",
    "/this-page-does-not-exist-404-check",
]


def status(url: str) -> tuple[int, int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "pond-fixes-404-check/1"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        code = r.status
    except urllib.error.HTTPError as e:
        r, code = e, e.code
    body = r.read()
    return code, len(body), r.headers.get("content-type", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://joinpond.ai")
    ap.add_argument("--expect-404", action="store_true")
    args = ap.parse_args()
    rows = []
    for p in PATHS:
        code, n, ctype = status(args.base + p)
        rows.append({"path": p, "status": code, "body_bytes": n, "content_type": ctype})
        print(f"{code}  {n:6d} B  {p}")
    soft = [r["path"] for r in rows if r["status"] == 200]
    print(f"\n{len(soft)} of {len(rows)} missing pages answer 200")
    out = {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "base": args.base,
        "rows": rows,
        "soft_404_count": len(soft),
    }
    if args.base == "https://joinpond.ai":
        (Path(__file__).parent / "results.json").write_text(
            json.dumps(out, indent=2) + "\n"
        )
    if args.expect_404 and any(r["status"] != 404 for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
