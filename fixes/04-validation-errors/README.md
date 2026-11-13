# 04. Validation errors that name the field

## I noticed
When arguments fail the schema, every tool says "Tool arguments do not match the input schema." (`live_errors.json`, captured 2026-11-13).
- PAS tools add a `path` and a `validationReason`. For a missing `requestId` the path is `/` and the reason is `schema_required`, so the missing field's name is absent. For `limit: 500` the path is `/limit` and the reason is `schema_maximum`, but the allowed maximum is not given.
- `pond_*` tools (tested with `pond_recent_updates`) return `"details":{}`, with no path at all.

An agent has to guess, retry, or read the whole schema again.

## Fix
`format_errors.py` runs the tool's own inputSchema through `jsonschema`. It returns one `{path, message}` per problem, with the constraint taken from the schema:

| Input | Server today | Fix |
|---|---|---|
| `pas_capabilities {}` | path `/`, schema_required | `/requestId`: requestId is required (string, 1-200 chars) |
| `pas_catalog_search {limit: 500}` | path `/limit`, schema_maximum | `/limit`: limit must be integer, 1-100; got 500 |
| `pas_catalog_search {q: ...}` | path `/`, schema_additionalProperties | `/q`: q is not a known field; allowed: cursor, filters, limit, query, requestId |
| `pond_recent_updates {kinds: ["news"]}` | `details: {}` | `/kinds/0`: kinds[0] must be one of "pas_update", "dataset_update", "customer_story", "official_announcement"; got "news" |

These would go in the existing `details` object, next to the current fields, which keeps the response compatible.

## Metric
Errors that name the failing field and the valid range: 1 of 4 cases today (`/limit`, without the range), 4 of 4 with the fix. I did not measure the retries this saves, since that would need many agent runs.

Run: `uv run python fixes/04-validation-errors/capture_live.py` (4 free calls).
Effort: S (estimate).
