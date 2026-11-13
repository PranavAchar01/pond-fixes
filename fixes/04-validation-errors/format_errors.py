"""Turn JSON Schema validation errors into errors an agent can fix in one retry.

Each error names the field as a JSON Pointer and says what a valid value
looks like, using the constraints already in the tool's inputSchema:

    {"path": "/requestId", "message": "requestId is required (string, 1-200 chars)"}
"""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def pointer(parts) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def describe(schema: dict) -> str:
    """Short human description of what a schema accepts, e.g. 'string, 1-200 chars'."""
    bits: list[str] = []
    if "enum" in schema:
        return "one of " + ", ".join(json.dumps(v) for v in schema["enum"])
    t = schema.get("type")
    if t:
        bits.append(t if isinstance(t, str) else " or ".join(t))
    lo, hi = schema.get("minLength"), schema.get("maxLength")
    if lo is not None and hi is not None:
        bits.append(f"{lo}-{hi} chars")
    elif hi is not None:
        bits.append(f"at most {hi} chars")
    elif lo is not None:
        bits.append(f"at least {lo} chars")
    lo, hi = schema.get("minimum"), schema.get("maximum")
    if lo is not None and hi is not None:
        bits.append(f"{lo}-{hi}")
    elif hi is not None:
        bits.append(f"at most {hi}")
    elif lo is not None:
        bits.append(f"at least {lo}")
    if schema.get("maxItems") is not None:
        bits.append(f"at most {schema['maxItems']} items")
    if "pattern" in schema:
        bits.append(f"matching {schema['pattern']}")
    return ", ".join(bits)


def _subschema(root: dict, path) -> dict:
    node = root
    for p in path:
        if isinstance(p, int):
            node = node.get("items", {})
        else:
            node = node.get("properties", {}).get(p, {})
    return node


def _name(path) -> str:
    """requestId, kinds[1], filters.region; 'arguments' for the root."""
    out = ""
    for p in path:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out or "arguments"


def format_error(err: ValidationError, root: dict) -> list[dict]:
    path = list(err.absolute_path)
    name = _name(path)
    v = err.validator
    if v == "required":
        out = []
        props = _subschema(root, path).get("properties", {})
        for field in err.validator_value:
            if field in (err.instance or {}):
                continue
            d = describe(props.get(field, {}))
            out.append(
                {
                    "path": pointer(path + [field]),
                    "message": f"{field} is required" + (f" ({d})" if d else ""),
                }
            )
        return out
    if v == "additionalProperties":
        allowed = sorted(_subschema(root, path).get("properties", {}))
        extra = sorted(set(err.instance) - set(allowed))
        return [
            {
                "path": pointer(path + [k]),
                "message": f"{k} is not a known field; allowed: {', '.join(allowed)}",
            }
            for k in extra
        ]
    if v in ("oneOf", "anyOf"):
        return [
            {
                "path": pointer(path),
                "message": f"{name} must match exactly one of the allowed shapes: "
                + "; ".join(_shape(s) for s in err.validator_value),
            }
        ]
    d = describe(err.schema)
    got = json.dumps(err.instance)
    if len(got) > 60:
        got = got[:57] + "..."
    return [{"path": pointer(path), "message": f"{name} must be {d}; got {got}"}]


def _shape(s: dict) -> str:
    req = s.get("required", [])
    banned = [x for n in [s.get("not", {})] for x in n.get("required", [])]
    txt = "provide " + " and ".join(req) if req else "any"
    if banned:
        txt += " without " + " and ".join(banned)
    return txt


def validate(schema: dict, instance: Any) -> list[dict]:
    """All errors for instance, sorted by path, in the {path, message} shape."""
    errs = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda e: list(e.absolute_path),
    )
    out: list[dict] = []
    for e in errs:
        out.extend(format_error(e, schema))
    return out
