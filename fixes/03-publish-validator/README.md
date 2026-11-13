# 03. Publish validator

## I noticed
Some published catalog items need tools that `tools/list` does not have. `competitor-review-themes` and `review-pain-finder` need `pond_record`, and `company-details` needs `pond_name`. One item, `ai-tech-zaozhidao`, lists its platform as `pond-grok-bot`. Every other item says `grokbot`.

## Fix
`validate_catalog.py` checks each item before it is published:
- error: a required capability named like a Pond tool (`pond_*`, `pas_*`) that is not in `tools/list`;
- error: a `compatiblePlatforms` value outside the allowed enum (`grokbot`);
- warning: any other capability name (`read`, `web-fetch`, `send-after-approval`, ...). These look like client-side capabilities, and Pond has no registry to check them against, so a person should sort them.

It exits 1 on errors, prints GitHub annotations with `--format github`, and `catalog-check.yml` runs it as a CI job.

## Metric (real data, data/catalog.txt + data/tools.txt)
- 4 errors in 4 items: the 3 missing tools above plus the platform typo. Today all 4 are live in the catalog.
- 39 warnings in 11 items for capability names that are not Pond tools.

Run: `uv run python fixes/03-publish-validator/validate_catalog.py`
Effort: S (estimate).
