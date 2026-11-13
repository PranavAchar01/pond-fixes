import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import export_shape as es


def test_url_shape_drops_only_base64_and_adds_url():
    exp = es.load_export()
    shaped = es.url_shape(exp)
    assert "package_base64" not in shaped
    assert set(exp) - {"package_base64"} <= set(shaped)
    assert (
        shaped["package_sha256"] == exp["package_sha256"]
    )  # client can still verify the download


def test_real_export_shrinks_by_more_than_90_percent():
    r = es.report()
    assert r["response_json_bytes_today"] > 130_000
    assert r["response_json_bytes_with_url"] < 0.1 * r["response_json_bytes_today"]
