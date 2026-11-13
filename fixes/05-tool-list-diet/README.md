# 05. Tool-list diet

## I noticed
`tools/list` is 359,514 bytes, about 89,698 tokens (ESTIMATE: chars / 4). A stateless server sends it to every session. The largest part is `outputSchema`, 207,161 chars across 89 tools, ahead of the descriptions. Several PAS envelopes repeat inside them; one 3,648-char subschema appears 12 times. 25 descriptions also carry whole procedures. `pond_scrape_start` alone has a 9,083-char description and a 12,255-char inputSchema.

## Fix
`diet.py` rewrites the real list (`data/tools_list.json`) with two levers and measures each one:
1. Description: keep the first paragraph, cut at a sentence end if it runs past 600 chars. The rest goes into one skill file (`skill/pond-tools/SKILL.md`, 27,011 bytes, one section per tool), and the description points to it. Nothing is deleted.
2. outputSchema: leave it out of `tools/list` and serve it on request. The MCP spec makes it optional. Results still return `structuredContent`.

inputSchema is unchanged.

## Metric (fixes/05-tool-list-diet/results.json)

| | compact JSON chars | est. tokens |
|---|---|---|
| today | 358,793 | 89,698 |
| lever 1 (descriptions) | 334,094 | 83,523 |
| levers 1 + 2 | 125,637 | 31,409 |

Lever 1 saves about 6,175 tokens per session for every client. Lever 2 saves about 52,114 more, but only for clients that put outputSchema into the model's context. I have not checked which clients do. All token figures are chars / 4 estimates.

Top 10 by size (bytes: description / inputSchema / outputSchema):
pond_scrape_start 22,260 (9,083 / 12,255 / 719), pas_install_report 13,264, pas_catalog_view 12,774, pond_workflow_update 12,256, pas_install_prepare 11,811, pond_workflow_draft 10,656, pas_install_status 10,475, pond_enrich 10,018, pas_install_prepare_batch 9,547, pond_investors 9,054.

Wire size: the server already gzips (46,801 bytes) when the client asks. Python's urllib, for one, does not ask.

Run: `uv run python fixes/05-tool-list-diet/diet.py --write-skill`
Effort: M (estimate). The descriptions are simple to move. Checking that agents still pick the right tool needs an eval.
