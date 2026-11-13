import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import analyze_landing as al


def make_site(tmp: Path) -> Path:
    a = tmp / "assets"
    a.mkdir(parents=True)
    (tmp / "index.html").write_text(
        '<script type="module" crossorigin src="/assets/entry.js"></script>'
        '<link rel="modulepreload" crossorigin href="/assets/react.js">'
        '<link rel="stylesheet" crossorigin href="/assets/app.css">'
    )
    (a / "entry.js").write_text(
        'import{a}from"./react.js";const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=['
        '"assets/landing.js","assets/wallet.js"])));'
        "x=r(`/`)({component:s(()=>F(()=>import(`./landing.js`),__vite__mapDeps([0])),`c`)});"
        "y=r(`/wallet`)({component:s(()=>F(()=>import(`./wallet.js`),__vite__mapDeps([1])),`c`)});"
    )
    (a / "react.js").write_text("export const a=1;")
    (a / "landing.js").write_text('import{t}from"./track.js";')
    (a / "track.js").write_text("posthog " * 60)
    (a / "wallet.js").write_text("privy walletconnect moonpay")
    (a / "app.css").write_text("body{}")
    return tmp


def test_landing_includes_route_chunk_and_static_imports_not_other_routes(tmp_path):
    r = al.analyze(make_site(tmp_path))
    assert r["landing_route_lazy_chunk"] == "landing.js"
    assert r["landing_total_js"]["files"] == 4  # entry, react, landing, track
    assert r["posthog_chunks_on_landing"]["names"] == ["track.js"]
    assert r["wallet_named_chunks_raw"] == 0  # wallet.js is only behind /wallet


def test_static_imports_parser():
    assert al.static_imports(
        'import{a as b}from"./x.js";import"./y.js";export{c}from"./z.js"'
    ) == {"x.js", "y.js", "z.js"}
