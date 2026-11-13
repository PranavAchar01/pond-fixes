"""Send a few invalid arguments to free, read-only Pond tools and record the
server's error text next to what format_errors.py would say for the same input.

run: uv run python fixes/04-validation-errors/capture_live.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from format_errors import validate

from tools.pond_client import PondClient

SCHEMAS = json.loads((HERE / "schemas.json").read_text())
CASES = [
    ("pas_capabilities", {}),
    ("pas_catalog_search", {"requestId": "r", "limit": 500}),
    ("pas_catalog_search", {"requestId": "r", "q": "investors"}),
    ("pond_recent_updates", {"kinds": ["news"]}),
]


def main() -> None:
    c = PondClient()
    c.initialize()
    rows = []
    for name, args in CASES:
        r = c.call(name, args)
        msg = r.message or {}
        server = msg.get("error") or {
            "isError": (msg.get("result") or {}).get("isError"),
            "text": PondClient.text(r),
        }
        rows.append(
            {
                "tool": name,
                "arguments": args,
                "server_response": server,
                "fixed_response": validate(SCHEMAS[name], args),
            }
        )
        time.sleep(1)
    out = {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases": rows,
    }
    (HERE / "live_errors.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
