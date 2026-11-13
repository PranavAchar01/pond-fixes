import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from format_errors import describe, validate

SCHEMAS = json.loads((Path(__file__).parent / "schemas.json").read_text())


def test_missing_required_names_field_and_constraints():
    assert validate(SCHEMAS["pas_capabilities"], {}) == [
        {"path": "/requestId", "message": "requestId is required (string, 1-200 chars)"}
    ]


def test_type_and_range_errors_name_the_field():
    errs = validate(SCHEMAS["pas_catalog_search"], {"requestId": "r", "limit": 500})
    assert errs == [
        {"path": "/limit", "message": "limit must be integer, 1-100; got 500"}
    ]


def test_unknown_field_lists_allowed():
    errs = validate(SCHEMAS["pas_capabilities"], {"requestId": "r", "reqId": "x"})
    assert errs[0]["path"] == "/reqId"
    assert "allowed: requestId" in errs[0]["message"]


def test_enum_inside_array_has_index_path():
    errs = validate(SCHEMAS["pond_recent_updates"], {"kinds": ["pas_update", "news"]})
    assert errs[0]["path"] == "/kinds/1"
    assert errs[0]["message"].startswith('kinds[1] must be one of "pas_update"')


def test_one_of_explains_shapes():
    errs = validate(SCHEMAS["pond_scrape_status"], {})
    assert errs[0]["path"] == ""
    assert "provide run_id without watch_id" in errs[0]["message"]


def test_valid_input_has_no_errors():
    assert (
        validate(
            SCHEMAS["pas_catalog_search"], {"requestId": "r", "query": "investors"}
        )
        == []
    )


def test_describe_enum_and_pattern():
    assert describe({"type": "string", "enum": ["a", "b"]}) == 'one of "a", "b"'
    assert describe({"type": "string", "pattern": "^x$"}) == "string, matching ^x$"
