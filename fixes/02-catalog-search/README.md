# 02. Catalog search that ranks instead of filtering

## I noticed
`pas_catalog_search` returns nothing for most plain-language queries. 13 of my 20 test queries came back empty, for example "who should I meet at a conference next week" and "check if a company uses shopify". That fits a search that needs every word to match.

## Fix
`ranker.py` is a BM25 ranker over name, subtitle, use cases, categories, description, summary claims and required capabilities, with weights per field, a light stemmer and stopwords. It ranks every item, so one missing word lowers the score instead of dropping the result. It runs on the 21 real catalog items (`data/catalog.txt`).

## Metric
`queries.json` holds 20 member-style queries, each with the solution(s) that should answer it. Some are plain keywords ("battlecard", "investors", "new YC founders"), which the live search should handle. The score is the share of queries with a relevant solution in the top 3.

| | top-3 hit rate | zero-result queries |
|---|---|---|
| live `pas_catalog_search` (2026-11-13) | 7/20 = 35% | 13 |
| BM25 fix | 19/20 = 95% | 0 |

The one miss is "check if a company uses shopify": the word Shopify never appears in Storefront Fit Check. `ranker.py` also has an optional synonym table that gets 20/20. I wrote it after seeing these queries, so it is tuned to this set, and I am not counting it as a result.

I wrote the queries myself, knowing the catalog. A set taken from real member search logs would be the fair test.

Run: `uv run python fixes/02-catalog-search/evaluate.py` (live, 20 free calls) or `--offline`.
Effort: S (estimate). Ranking 21 to a few hundred items in memory needs no search service.
