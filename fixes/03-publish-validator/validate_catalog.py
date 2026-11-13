"""CI check for PAS catalog items before publish.

Errors (exit 1):
  - a required capability that looks like a Pond server tool (pond_* or pas_*)
    but is not in tools/list. The item cannot run on Pond as published.
  - a compatiblePlatforms value outside the allowed enum.
Warnings (exit 0 unless --strict):
  - a required capability that is not a Pond tool and not in the declared
    client-capability registry (for example "read", "web-fetch"). Pond has no
    registry today, so these are reported for a human to classify.

run: uv run python fixes/03-publish-validator/validate_catalog.py [--format github] [--strict]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fixes.common.data import catalog_items, tool_names

ALLOWED_PLATFORMS = {"grokbot"}
SERVER_PREFIXES = ("pond_", "pas_")


@dataclass
class Finding:
    level: str  # "error" | "warning"
    solution_id: str
    field: str
    value: str
    message: str


def check_item(
    item: dict, tools: set[str], client_caps: set[str] = frozenset()
) -> list[Finding]:
    sid = item["locator"]["solutionId"]
    out: list[Finding] = []
    for cap in item.get("requiredConnectorCapabilities", []):
        if cap in tools or cap in client_caps:
            continue
        if cap.startswith(SERVER_PREFIXES):
            out.append(
                Finding(
                    "error",
                    sid,
                    "requiredConnectorCapabilities",
                    cap,
                    f"{cap} is not a tool in tools/list; the item cannot run as published",
                )
            )
        else:
            out.append(
                Finding(
                    "warning",
                    sid,
                    "requiredConnectorCapabilities",
                    cap,
                    f"{cap} is neither a Pond tool nor a declared client capability",
                )
            )
    for p in item.get("compatiblePlatforms", []):
        if p not in ALLOWED_PLATFORMS:
            out.append(
                Finding(
                    "error",
                    sid,
                    "compatiblePlatforms",
                    p,
                    f"platform {p!r} is not one of {sorted(ALLOWED_PLATFORMS)}",
                )
            )
    return out


def check_catalog(
    items: list[dict], tools: set[str], client_caps: set[str] = frozenset()
) -> list[Finding]:
    return [f for it in items for f in check_item(it, tools, client_caps)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["text", "json", "github"], default="text")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()
    findings = check_catalog(catalog_items(), tool_names())
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            if args.format == "github":
                kind = "error" if f.level == "error" else "warning"
                print(f"::{kind} title={f.solution_id}::{f.field}: {f.message}")
            else:
                print(f"{f.level.upper():7} {f.solution_id}: {f.message}")
        broken = sorted({f.solution_id for f in errors})
        print(
            f"\n{len(errors)} errors in {len(broken)} items ({', '.join(broken)}); "
            f"{len(warnings)} warnings in {len({f.solution_id for f in warnings})} items"
        )
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
