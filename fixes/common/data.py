"""Loaders for the captured Pond responses in data/."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _json_after_header(text: str) -> dict:
    return json.loads(text[text.index("{") :])


def catalog_items() -> list[dict]:
    """The 21 items from pas_catalog_search, captured 2026-11-12."""
    return _json_after_header((DATA / "catalog.txt").read_text())["data"]["items"]


def tool_names() -> set[str]:
    """Tool names from tools/list, captured 2026-11-12."""
    return set(re.findall(r"^- (\w+):", (DATA / "tools.txt").read_text(), re.MULTILINE))


def tool_descriptions() -> dict[str, str]:
    text = (DATA / "tools.txt").read_text()
    out = {}
    for m in re.finditer(
        r"^- (\w+): (.*?)(?=^- \w+: |\Z)", text, re.MULTILINE | re.DOTALL
    ):
        out[m.group(1)] = m.group(2).strip()
    return out
