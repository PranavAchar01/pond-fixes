"""One number for the whole build: what an agent loads, and how long a member waits, to build one
workflow and learn whether it works. Today versus with the fixes in this repo applied.

Inputs are files captured during my build on 2026-11-12 (data/build-session, data/export.out,
data/tools_list.json) and the results files of fixes 05, 06 and 13. Writes bench/session.json.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "data" / "build-session"


def body_bytes(path: Path) -> int:
    text = path.read_text()
    return len(text[text.index("{") :].encode())


def run() -> dict:
    diet = json.loads((ROOT / "fixes/05-tool-list-diet/results.json").read_text())
    export = json.loads((ROOT / "fixes/06-export-by-url/results.json").read_text())
    preview = json.loads(
        (ROOT / "fixes/13-preview-before-confirm/results.json").read_text()
    )

    calls = {p.name: body_bytes(p) for p in sorted(SESSION.glob("*.out"))}
    calls["export.out"] = export["response_json_bytes_today"]
    get_json = json.loads((SESSION / "get.out").read_text().split("\n", 1)[1])
    get_without_files = len(
        json.dumps({k: v for k, v in get_json.items() if k != "pas_files"}).encode()
    )

    before = {"tools/list": diet["bytes_before"], **calls}
    after = dict(before)
    after["tools/list"] = diet["bytes_after_descriptions"]
    after["export.out"] = export["response_json_bytes_with_url"]
    # Same signed-URL change as fix 06, applied to pond_workflow_get, which returns the package files inline too.
    after["get.out"] = get_without_files + 200
    after_schema_clients = dict(
        after, **{"tools/list": diet["bytes_after_descriptions_and_output_schema"]}
    )

    b, a, s = (
        sum(before.values()),
        sum(after.values()),
        sum(after_schema_clients.values()),
    )
    wait = preview["brief_to_first_verdict_s"]
    return {
        "source": "data/build-session, data/export.out, fixes/05, 06 and 13 results.json",
        "bytes_loaded_per_build": {
            "before": b,
            "after": a,
            "after_for_clients_that_load_outputSchema": s,
            "reduction": round(1 - a / b, 3),
            "reduction_outputSchema_clients": round(1 - s / b, 3),
            "by_call_before": before,
            "by_call_after": after,
        },
        "estimated_tokens_per_build": {
            "before": b // 4,
            "after": a // 4,
            "after_outputSchema_clients": s // 4,
            "formula": "ESTIMATE: bytes / 4",
        },
        "brief_to_first_verdict_s": wait,
        "wait_reduction": preview["reduction"],
        "notes": [
            "Bytes are JSON response bodies the agent reads during the build, plus the tools/list result it loads at the start.",
            "get.out after = the same response without pas_files, plus about 200 bytes for a signed URL.",
            "Wait times come from one build, so treat them as one observed case, not an average.",
        ],
    }


if __name__ == "__main__":
    out = run()
    (ROOT / "bench" / "session.json").write_text(json.dumps(out, indent=2) + "\n")
    bl, w = out["bytes_loaded_per_build"], out["brief_to_first_verdict_s"]
    print(
        f"bytes per build {bl['before']:,} -> {bl['after']:,} ({bl['reduction']:.0%}); {bl['after_for_clients_that_load_outputSchema']:,} ({bl['reduction_outputSchema_clients']:.0%}) for outputSchema clients"
    )
    print(
        f"brief to first verdict {w['before']} s -> {w['after']} s ({out['wait_reduction']:.0%})"
    )
