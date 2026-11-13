"""Build routes.json (the list of real SPA paths) from the built Vite entry.

TanStack Router file routes appear in the bundle as a(`/path`)({...}).
Pathless layouts (segments starting with _) are dropped, $params become
:params. Run after `vite build` in CI and ship routes.json with the Worker.

run: uv run python fixes/08-soft-404/extract_routes.py dist/assets/index-*.js > routes.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROUTE = re.compile(r"\ba\(`(/[^`]*)`\)\(\{")


def normalize(route: str) -> str:
    segs = [s for s in route.strip("/").split("/") if s and not s.startswith("_")]
    segs = [":" + s[1:] if s.startswith("$") else s for s in segs]
    return "/" + "/".join(segs)


def extract(entry_js: str) -> list[str]:
    return sorted({normalize(r) for r in ROUTE.findall(entry_js)})


def main() -> None:
    print(json.dumps(extract(Path(sys.argv[1]).read_text(errors="replace")), indent=1))


if __name__ == "__main__":
    main()
