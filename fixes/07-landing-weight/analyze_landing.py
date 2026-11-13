"""What the joinpond.ai landing route loads, from a static mirror of the site.

First load = the entry script, every <link rel=modulepreload>, the stylesheet,
and the transitive static imports of those chunks. Dynamic import() targets
are not counted. Each first-load chunk is scanned for wallet / crypto onramp
markers; chunks where markers appear are listed with raw and gzip bytes.

run: uv run python fixes/07-landing-weight/analyze_landing.py MIRROR_DIR
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

MARKERS = [
    "privy",
    "walletconnect",
    "moonpay",
    "farcaster",
    "solana",
    "coinbase",
    "metamask",
    "wagmi",
    "viem",
    "onramp",
    "crypto-deposit",
    "siwe",
    "eip-1193",
]
STATIC_IMPORT = re.compile(
    r'(?:import|export)\s*(?:[\w*{}\s,$]+?\s*from\s*)?["\'](\./[^"\']+\.js)["\']'
)
DYNAMIC_IMPORT = re.compile(r'import\(\s*["\'](\./[^"\']+\.js)["\']\s*\)')


def head_refs(html: str) -> tuple[str, list[str], list[str]]:
    entry = re.search(r'<script type="module"[^>]*src="/assets/([^"]+)"', html).group(1)
    preloads = re.findall(r'rel="modulepreload"[^>]*href="/assets/([^"]+)"', html)
    css = re.findall(r'rel="stylesheet"[^>]*href="/assets/([^"]+)"', html)
    return entry, preloads, css


def static_imports(js: str) -> set[str]:
    return {m[2:] for m in STATIC_IMPORT.findall(js)}


def dynamic_imports(js: str) -> set[str]:
    return {m[2:] for m in DYNAMIC_IMPORT.findall(js)}


def closure(assets: Path, roots: list[str]) -> set[str]:
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        name = stack.pop()
        if name in seen or not (assets / name).exists():
            continue
        seen.add(name)
        stack.extend(static_imports((assets / name).read_text(errors="replace")))
    return seen


def markers_in(text: str) -> dict[str, int]:
    low = text.lower()
    return {m: low.count(m) for m in MARKERS if m in low}


def gz(data: bytes) -> int:
    return len(gzip.compress(data, compresslevel=9))


def br(data: bytes) -> int:
    import brotli

    return len(brotli.compress(data, quality=11))


def map_deps(entry_js: str) -> list[str]:
    """The __vite__mapDeps file table: index -> asset file name."""
    table = re.search(r"m\.f=\[(.*?)\]", entry_js)
    return re.findall(r'"assets/([^"]+)"', table.group(1)) if table else []


def route_deps(entry_js: str, route: str) -> list[str]:
    """Files __vitePreload fetches when the router matches `route`."""
    table = map_deps(entry_js)
    m = re.search(
        r"\(`"
        + re.escape(route)
        + r"`\)\(\{component:[^;]*?__vite__mapDeps\(\[([\d,]+)\]\)",
        entry_js,
    )
    return [table[int(i)] for i in m.group(1).split(",")] if m else []


def sizes(assets: Path, names) -> dict:
    data = [(assets / n).read_bytes() for n in names if (assets / n).exists()]
    return {
        "files": len(data),
        "raw": sum(map(len, data)),
        "gzip": sum(gz(d) for d in data),
        "brotli": sum(br(d) for d in data),
    }


def analyze(site: Path) -> dict:
    assets = site / "assets"
    html = (site / "index.html").read_text()
    entry, preloads, css = head_refs(html)
    first = closure(assets, [entry, *preloads])
    entry_js = (assets / entry).read_text(errors="replace")
    landing_route = route_deps(entry_js, "/")
    landing = first | closure(assets, landing_route)
    rows = []
    for name in sorted(landing):
        data = (assets / name).read_bytes()
        rows.append(
            {
                "chunk": name,
                "raw": len(data),
                "gzip": gz(data),
                "markers": markers_in(data.decode(errors="replace")),
            }
        )
    css_rows = [
        {
            "file": c,
            "raw": (assets / c).stat().st_size,
            "gzip": gz((assets / c).read_bytes()),
        }
        for c in css
    ]
    crypto = [r for r in rows if r["markers"]]
    # Chunks named after wallet / onramp code: these exist only for that feature.
    named = re.compile(
        r"walletconnect|crypto|onramp|wallet|privy|farcaster|solana|coinbase|moonpay",
        re.IGNORECASE,
    )
    crypto_named = [r for r in crypto if named.search(r["chunk"])]
    media = sorted(
        set(
            re.findall(
                r'["\'(](/images/[^"\')\s]+\.(?:mp4|webm|webp|png|jpg|jpeg|avif|svg))',
                html,
            )
        )
    )
    analytics = [
        n
        for n in landing
        if "posthog" in (assets / n).read_text(errors="replace").lower()
        and (assets / n).read_text(errors="replace").lower().count("posthog") > 50
    ]
    return {
        "entry": entry,
        "static_first_load": sizes(assets, first),
        "landing_route_lazy_chunk": landing_route[0] if landing_route else None,
        "landing_total_js": sizes(assets, landing),
        "landing_total_css": sizes(assets, css),
        "posthog_chunks_on_landing": {"names": analytics, **sizes(assets, analytics)},
        "modulepreload_count": len(preloads),
        "css": css_rows,
        "chunks_with_wallet_markers": sorted(crypto, key=lambda r: -r["raw"]),
        "chunks_with_wallet_markers_raw": sum(r["raw"] for r in crypto),
        "chunks_with_wallet_markers_gzip": sum(r["gzip"] for r in crypto),
        "wallet_named_chunks_raw": sum(r["raw"] for r in crypto_named),
        "wallet_named_chunks_gzip": sum(r["gzip"] for r in crypto_named),
        "media_in_index_html": media,
        "compression_note": "gzip -9 and brotli -q11 computed locally on the mirror files; joinpond.ai served gzip to an Accept-Encoding: br, gzip request (see headers.json).",
    }


def main() -> None:
    site = Path(sys.argv[1])
    r = analyze(site)
    (Path(__file__).parent / "results.json").write_text(json.dumps(r, indent=2) + "\n")
    s = {k: v for k, v in r.items() if k != "chunks_with_wallet_markers"}
    print(json.dumps(s, indent=2))
    for c in r["chunks_with_wallet_markers"][:25]:
        print(f"{c['raw']:8d} {c['gzip']:7d} {c['chunk']} {c['markers']}")


if __name__ == "__main__":
    main()
