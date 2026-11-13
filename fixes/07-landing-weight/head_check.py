"""Plain HTTP HEAD requests against joinpond.ai for the landing route's files.

Records status, content-length, content-encoding, cache-control and the
Cloudflare cache status. No page is rendered and no script runs.

run: uv run python fixes/07-landing-weight/head_check.py
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://joinpond.ai"
PATHS = [
    "/",
    "/assets/index-BbtYghut.js",
    "/assets/track-DKHn3SyZ.js",
    "/assets/routes-PvcBNCWd.js",
    "/assets/ClosingSection-p5k3UqqF.js",
    "/assets/index-u1-B8PNS.css",
    "/images/landing-page-202610/video/pond-100notext.webm",
    "/images/landing-page-202610/video/pond-100notext.mp4",
    "/images/landing-page-202610/video/pond-100notext-baked.mp4",
    "/images/landing-page-202610/video/pond-100notext-baked-sm.mp4",
    "/images/landing-page-202610/video/pond-connect-intro.webm",
]
KEEP = [
    "content-type",
    "content-length",
    "content-encoding",
    "cache-control",
    "cf-cache-status",
    "age",
    "server",
    "vary",
]


def head(url: str, accept_encoding: str = "br, gzip") -> dict:
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={
            "Accept-Encoding": accept_encoding,
            "User-Agent": "pond-fixes-head-check/1",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        status = resp.status
    except urllib.error.HTTPError as e:
        resp, status = e, e.code
    h = {k.lower(): v for k, v in resp.headers.items()}
    return {"status": status, **{k: h.get(k) for k in KEEP}}


def main() -> None:
    out = {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "accept_encoding_sent": "br, gzip",
        "results": {},
    }
    for p in PATHS:
        out["results"][p] = head(BASE + p)
        print(p, json.dumps(out["results"][p]))
    (Path(__file__).parent / "headers.json").write_text(
        json.dumps(out, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
