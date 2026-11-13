"""pond_workflow_export today returns the whole .pas package inline as base64.
This compares the bytes an agent receives today with a signed-URL response
that carries the same metadata plus a short-lived download link.

run: uv run python fixes/06-export-by-url/export_shape.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fixes.common.data import DATA

# Shape of the signed link. Length matches a typical S3/R2 presigned GET URL
# (about 450 to 600 chars); the exact value is a placeholder.
EXAMPLE_URL = (
    "https://files.joinpond.ai/exports/pw_1058be43f6482ca64fa86b7d/statsmodels-question-digest-1.0.0.pas"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXXXXXXXXXXXXXXXX%2F20261112%2Fauto%2Fs3%2Faws4_request"
    "&X-Amz-Date=20261112T225000Z&X-Amz-Expires=900&X-Amz-SignedHeaders=host"
    "&X-Amz-Signature=" + "0" * 64
)


def load_export(path: Path = DATA / "export.out") -> dict:
    text = path.read_text()
    return json.loads(text[text.index("{") :])


def url_shape(export: dict, url: str = EXAMPLE_URL) -> dict:
    """Same response, package by reference instead of inline."""
    out = {k: v for k, v in export.items() if k != "package_base64"}
    out["package_url"] = url
    out["package_url_expires_in_s"] = 900
    return out


def size(obj: dict) -> int:
    return len(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode())


def report() -> dict:
    raw_file = (DATA / "export.out").read_bytes()
    exp = load_export()
    before = size(exp)
    after = size(url_shape(exp))
    return {
        "source": "data/export.out (pond_workflow_export on pw_1058be43f6482ca64fa86b7d, 2026-11-12)",
        "export_out_file_bytes": len(raw_file),
        "response_json_bytes_today": before,
        "package_base64_chars": len(exp["package_base64"]),
        "package_bytes_declared": exp.get("package_bytes"),
        "response_json_bytes_with_url": after,
        "bytes_saved_per_export": before - after,
        "share_of_response_that_is_base64": round(
            len(exp["package_base64"]) / before, 3
        ),
        "estimated_tokens_today": before // 4,
        "estimated_tokens_with_url": after // 4,
        "estimated_tokens_saved_per_export": (before - after) // 4,
        "tokens_formula": "ESTIMATE: bytes / 4. Base64 tokenizes worse than prose, so this likely undercounts.",
        "exports_per_build_observed": 1,
    }


def main() -> None:
    r = report()
    (Path(__file__).parent / "results.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
