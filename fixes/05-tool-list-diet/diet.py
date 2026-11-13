"""Shrink tools/list without losing anything an agent needs to pick a tool.

Lever 1, description: keep the first paragraph, move the rest (procedures,
caveats, examples) into one skill file the agent reads when it uses the tool.
Lever 2, outputSchema: drop it from tools/list and serve it on demand. The
MCP spec makes outputSchema optional. Results still carry structuredContent.

Reports bytes and estimated tokens (chars / 4, an ESTIMATE) before and after on
the real tools/list captured in data/tools_list.json, and the top 10 tools by
size.

run: uv run python fixes/05-tool-list-diet/diet.py [--write-skill]
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from fixes.common.data import DATA

MAX_FIRST_PARAGRAPH = (
    600  # chars; a longer first paragraph is cut at the sentence before this
)


def size(obj) -> int:
    return len(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def first_paragraph(text: str) -> tuple[str, str]:
    """(kept, moved). Split at the first blank line; very long first paragraphs
    are cut at the last sentence end before MAX_FIRST_PARAGRAPH."""
    text = (text or "").strip()
    parts = re.split(r"\n\s*\n", text, maxsplit=1)
    head, rest = parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")
    if len(head) > MAX_FIRST_PARAGRAPH:
        cut = max(
            head.rfind(". ", 0, MAX_FIRST_PARAGRAPH),
            head.rfind(".\n", 0, MAX_FIRST_PARAGRAPH),
        )
        if cut > 0:
            head, rest = (
                head[: cut + 1],
                (head[cut + 1 :].strip() + ("\n\n" + rest if rest else "")).strip(),
            )
    return head, rest


def slim(
    tools: list[dict], drop_output_schema: bool
) -> tuple[list[dict], dict[str, str]]:
    out, moved = [], {}
    for t in tools:
        t2 = copy.deepcopy(t)
        keep, rest = first_paragraph(t.get("description", ""))
        if rest:
            t2["description"] = (
                keep + f" Full procedure: skill pond-tools, section {t['name']}."
            )
            moved[t["name"]] = rest
        if drop_output_schema:
            t2.pop("outputSchema", None)
        out.append(t2)
    return out, moved


def skill_file(moved: dict[str, str]) -> str:
    lines = [
        "---",
        "name: pond-tools",
        (
            "description: Procedures and caveats for Pond MCP tools, one section per tool. "
            "Read the section for a tool before calling it."
        ),
        "---",
        "",
    ]
    for name, text in sorted(moved.items()):
        lines += [f"## {name}", "", text, ""]
    return "\n".join(lines)


def report(tools: list[dict]) -> dict:
    full = {"tools": tools}
    desc_only, moved = slim(tools, drop_output_schema=False)
    both, _ = slim(tools, drop_output_schema=True)
    before = size(full)
    a, b = size({"tools": desc_only}), size({"tools": both})
    offenders = sorted(tools, key=lambda t: -size(t))[:10]
    return {
        "source": "data/tools_list.json (tools/list result, captured by bench/measure.py)",
        "tool_count": len(tools),
        "bytes_before": before,
        "bytes_after_descriptions": a,
        "bytes_after_descriptions_and_output_schema": b,
        "description_chars_before": sum(len(t.get("description", "")) for t in tools),
        "description_chars_after": sum(
            len(t.get("description", "")) for t in desc_only
        ),
        "output_schema_bytes": sum(
            size(t["outputSchema"]) for t in tools if "outputSchema" in t
        ),
        "tools_with_text_moved": len(moved),
        "skill_file_bytes": len(skill_file(moved).encode()),
        "estimated_tokens_before": before // 4,
        "estimated_tokens_after_descriptions": a // 4,
        "estimated_tokens_after_both": b // 4,
        "tokens_formula": "ESTIMATE: chars / 4 of the compact JSON",
        "top10": [
            {
                "name": t["name"],
                "bytes": size(t),
                "description": len(t.get("description", "")),
                "inputSchema": size(t.get("inputSchema", {})),
                "outputSchema": size(t.get("outputSchema", {})),
            }
            for t in offenders
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write-skill", action="store_true", help="write skill/pond-tools/SKILL.md"
    )
    args = ap.parse_args()
    tools = json.loads((DATA / "tools_list.json").read_text())["tools"]
    r = report(tools)
    (HERE / "results.json").write_text(json.dumps(r, indent=2) + "\n")
    if args.write_skill:
        _, moved = slim(tools, False)
        (HERE / "skill" / "pond-tools").mkdir(parents=True, exist_ok=True)
        (HERE / "skill" / "pond-tools" / "SKILL.md").write_text(skill_file(moved))
    print(json.dumps({k: v for k, v in r.items() if k != "top10"}, indent=2))
    for t in r["top10"]:
        print(
            f"{t['bytes']:7d}  desc {t['description']:5d}  in {t['inputSchema']:6d}  out {t['outputSchema']:6d}  {t['name']}"
        )


if __name__ == "__main__":
    main()
