"""Measure the Pond MCP server with free, read-only calls only.

Writes bench/results.json: latency p50/p95 per call (N sequential calls, 1 s
apart), tools/list size raw and with Accept-Encoding gzip / br, the
Content-Encoding the server answered with, and whether initialize returns an
Mcp-Session-Id. Response bodies are not stored (pond_current_user carries the
member's email); only timings, sizes and counts are kept.

run: uv run python bench/measure.py [--n 15]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pond_client import PondClient

OUT = Path(__file__).resolve().parent / "results.json"

CALLS = {
    "pond_current_user": ("tools/call", {"name": "pond_current_user", "arguments": {}}),
    "pas_catalog_search": (
        "tools/call",
        {
            "name": "pas_catalog_search",
            "arguments": {"requestId": "bench", "query": "investors"},
        },
    ),
    "pas_capabilities": (
        "tools/call",
        {"name": "pas_capabilities", "arguments": {"requestId": "bench"}},
    ),
    "tools/list": ("tools/list", {}),
    "pond_recent_updates": (
        "tools/call",
        {"name": "pond_recent_updates", "arguments": {"limit": 20}},
    ),
}


def pct(values: list[float], q: float) -> float:
    """Nearest-rank percentile."""
    s = sorted(values)
    k = max(0, min(len(s) - 1, round(q / 100 * len(s) + 0.5) - 1))
    return s[k]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--spacing", type=float, default=1.0)
    args = ap.parse_args()

    c = PondClient()
    init = c.initialize()
    results: dict = {
        "server": c.url,
        "started_at": now(),
        "method": (
            f"N={args.n} sequential calls per tool, {args.spacing}s apart, one client on the author's machine; "
            "wall time from request send to full body read (includes "
            "TLS reuse effects of urllib, which opens a new connection per request)."
        ),
        "initialize": {
            "status": init.status,
            "returns_mcp_session_id": init.session_id is not None,
            "seconds": round(init.seconds, 3),
        },
        "latency": {},
    }

    for name, (method, params) in CALLS.items():
        times, sizes, errors = [], [], 0
        for i in range(args.n):
            r = c.rpc(method, params)
            times.append(r.seconds * 1000)
            sizes.append(r.body_bytes)
            msg = r.message or {}
            if (
                r.status >= 400
                or "error" in msg
                or (msg.get("result") or {}).get("isError")
            ):
                errors += 1
            if i < args.n - 1:
                time.sleep(args.spacing)
        entry = {
            "n": args.n,
            "p50_ms": round(statistics.median(times), 1),
            "p95_ms": round(pct(times, 95), 1),
            "min_ms": round(min(times), 1),
            "max_ms": round(max(times), 1),
            "errors": errors,
            "body_bytes_median": int(statistics.median(sizes)),
            "measured_at": now(),
        }
        if name == "pond_recent_updates":
            text = PondClient.text(r)
            try:
                data = json.loads(text)
                items = data.get("updates", data.get("items", data.get("results", [])))
                entry["items_returned"] = (
                    len(items) if isinstance(items, list) else None
                )
            except json.JSONDecodeError:
                entry["items_returned"] = None
            entry["response_text_if_short"] = text if len(text) < 400 else None
        results["latency"][name] = entry
        print(name, entry["p50_ms"], entry["p95_ms"], file=sys.stderr)

    sizes: dict = {}
    for label, enc in (("identity", None), ("gzip", "gzip"), ("br", "br")):
        hdr = {"Accept-Encoding": enc} if enc else {}
        r = c.rpc("tools/list", {}, extra_headers=hdr)
        sizes[label] = {
            "accept_encoding_sent": enc,
            "content_encoding_received": r.headers.get("content-encoding"),
            "wire_bytes": r.raw_bytes,
            "decoded_bytes": r.body_bytes,
            "measured_at": now(),
        }
    tools = r.message["result"]["tools"]
    # Tool definitions are public; saved so fixes/05 can run offline on the real list.
    (OUT.parents[1] / "data" / "tools_list.json").write_text(
        json.dumps(r.message["result"], ensure_ascii=False, indent=1) + "\n"
    )
    compact = json.dumps(r.message["result"], ensure_ascii=False, separators=(",", ":"))
    desc_chars = sum(len(t.get("description") or "") for t in tools)
    schema_chars = sum(
        len(json.dumps(t.get("inputSchema"), ensure_ascii=False, separators=(",", ":")))
        for t in tools
    )
    results["tools_list"] = {
        "tool_count": len(tools),
        "by_accept_encoding": sizes,
        "server_compresses": any(
            v["content_encoding_received"] for v in sizes.values()
        ),
        "result_chars_compact": len(compact),
        "description_chars": desc_chars,
        "input_schema_chars": schema_chars,
        "estimated_tokens": len(compact) // 4,
        "estimated_tokens_formula": "ESTIMATE: characters / 4 of the compact JSON result object",
    }
    results["finished_at"] = now()
    OUT.write_text(json.dumps(results, indent=2) + "\n")
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
