import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import extract_routes as er

BUNDLE = (
    "vs=a(`/`)({component:x}),js=a(`/register`)({validateSearch:y}),"
    "k=a(`/_app/workflows/$workflowId`)({component:z}),m=a(`/_app/brain/team/$teamId/`)({c:1})"
)


def test_normalize_drops_pathless_layout_and_maps_params():
    assert er.normalize("/_app/workflows/$workflowId") == "/workflows/:workflowId"
    assert er.normalize("/") == "/"
    assert er.normalize("/_app/brain/team/$teamId/") == "/brain/team/:teamId"


def test_extract_from_bundle():
    assert er.extract(BUNDLE) == [
        "/",
        "/brain/team/:teamId",
        "/register",
        "/workflows/:workflowId",
    ]


def test_routes_json_matches_live_bundle_routes():
    import json

    routes = json.loads((Path(__file__).parent / "routes.json").read_text())
    assert "/" in routes and "/workflows/:workflowId" in routes
    for missing in [
        "/docs",
        "/pricing",
        "/catalog",
        "/help",
        "/marketplace",
        "/changelog",
        "/status",
    ]:
        assert missing not in routes
