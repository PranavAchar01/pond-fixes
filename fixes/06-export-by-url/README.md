# 06. Export by URL

## I noticed
`pond_workflow_export` puts the whole `.pas` package inline as `package_base64`. For my 12-file workflow the response was 140,226 bytes, and 133,104 of them (94.9%) were base64 that the agent cannot read. All of it went into the agent's context.

## Fix
Return the same response without `package_base64`, plus a signed `package_url` that expires in 900 s. The response already has `package_sha256`, so the client can still verify the download. Pond already signs 15-minute download links in `pas_install_grant`. `export_shape.py` builds the new shape from the real export and measures both.

## Metric (fixes/06-export-by-url/results.json)
- Today: 140,226 bytes, about 35,056 tokens.
- With URL: 7,510 bytes, about 1,877 tokens.
- Saved per export: 132,716 bytes, about 33,179 tokens (ESTIMATE: bytes / 4; base64 tokenizes worse than prose, so this probably undercounts). My build exported once.

Related, not counted: `pond_workflow_get` returns all `pas_files` inline (35,847 bytes in `get.out`), and every write response repeats the 2,543-byte `display_graph`.

Run: `uv run python fixes/06-export-by-url/export_shape.py`
Effort: S (estimate).
