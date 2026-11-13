import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import diet


def test_first_paragraph_split():
    keep, rest = diet.first_paragraph("Find things.\n\nStep 1. Do x.\n\nStep 2. Do y.")
    assert keep == "Find things." and rest.startswith("Step 1.") and "Step 2." in rest


def test_long_single_paragraph_is_cut_at_sentence():
    text = ("Sentence one is here. " * 40).strip()
    keep, rest = diet.first_paragraph(text)
    assert len(keep) <= diet.MAX_FIRST_PARAGRAPH and keep.endswith(".") and rest


def test_slim_keeps_schema_and_name_and_points_to_skill():
    tools = [
        {
            "name": "t",
            "description": "Short.\n\nLong procedure.",
            "inputSchema": {"type": "object"},
            "outputSchema": {"type": "object"},
        }
    ]
    out, moved = diet.slim(tools, drop_output_schema=True)
    assert out[0]["inputSchema"] == {"type": "object"} and "outputSchema" not in out[0]
    assert "skill pond-tools" in out[0]["description"] and moved == {
        "t": "Long procedure."
    }


def test_nothing_is_lost_text_is_moved_to_skill():
    tools = [{"name": "a", "description": "One.\n\nTwo three."}]
    _, moved = diet.slim(tools, False)
    assert "## a" in diet.skill_file(moved) and "Two three." in diet.skill_file(moved)


def test_real_tools_list_shrinks():
    import json

    tools = json.loads((diet.DATA / "tools_list.json").read_text())["tools"]
    r = diet.report(tools)
    assert r["tool_count"] == 89
    assert (
        r["bytes_after_descriptions_and_output_schema"]
        < r["bytes_after_descriptions"]
        < r["bytes_before"]
    )
