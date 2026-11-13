# 11. One-transaction confirm

## I noticed
`pond_workflow_confirm` on my workflow returned `status: "confirmed"` and `live_version: 3`. In the same response, `actor_name` still read "[Editing] Statsmodels question digest" and `actor_note` still read "Building the weekday digest". The "[Deployed]" name appeared only as an instruction, `agent.rename_to`, for the client to apply later (`confirm.out`). Anyone who reads the workflow before the client acts sees a confirmed workflow labelled as being edited.

## Fix
`confirm.py` sets `status`, `live_version`, `actor_name`, `actor_note` and `actor_at` in a single UPDATE inside one transaction, guarded by `expected_revision`. Readers see either the old state or the new one, and a confirm against an old revision is rejected with nothing changed. `consistent()` is the rule any reader can check.

## Metric
Fields left stale by confirm: 2 in the observed response (`actor_name`, `actor_note`), 0 with the fix. `test_observed_confirm_response_breaks_the_invariant` runs the rule on the real response, and `test_concurrent_reader_never_sees_a_mix` checks a reader during a half-done write.

Run: `uv run pytest -q fixes/11-confirm-transaction`
Effort: S (estimate).
