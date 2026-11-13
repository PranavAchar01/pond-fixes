import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import validate_catalog as vc

from fixes.common.data import catalog_items, tool_names


def item(sid, caps=(), platforms=("grokbot",)):
    return {
        "locator": {"solutionId": sid},
        "requiredConnectorCapabilities": list(caps),
        "compatiblePlatforms": list(platforms),
    }


def test_missing_pond_tool_is_error():
    f = vc.check_item(item("x", ["pond_record"]), {"pond_web_read"})
    assert [(x.level, x.value) for x in f] == [("error", "pond_record")]


def test_present_tool_passes():
    assert vc.check_item(item("x", ["pond_web_read"]), {"pond_web_read"}) == []


def test_client_capability_is_warning_unless_declared():
    assert vc.check_item(item("x", ["read"]), set())[0].level == "warning"
    assert vc.check_item(item("x", ["read"]), set(), {"read"}) == []


def test_platform_typo_is_error():
    f = vc.check_item(item("x", platforms=["pond-grok-bot"]), set())
    assert f[0].level == "error" and f[0].field == "compatiblePlatforms"


def test_real_catalog_flags_three_broken_items_and_platform_typo():
    findings = vc.check_catalog(catalog_items(), tool_names())
    missing_tools = {
        (f.solution_id, f.value)
        for f in findings
        if f.level == "error" and f.field == "requiredConnectorCapabilities"
    }
    assert missing_tools == {
        ("competitor-review-themes", "pond_record"),
        ("review-pain-finder", "pond_record"),
        ("company-details", "pond_name"),
    }
    platform = [
        (f.solution_id, f.value) for f in findings if f.field == "compatiblePlatforms"
    ]
    assert platform == [("ai-tech-zaozhidao", "pond-grok-bot")]
