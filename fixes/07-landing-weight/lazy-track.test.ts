import { test } from "node:test";
import assert from "node:assert/strict";
import { createTracker } from "./lazy-track.ts";

test("events before load are queued, then delivered in order", async () => {
  const seen: string[] = [];
  let fire: () => void = () => {};
  const t = createTracker(async () => ({ capture: (e) => seen.push(e) }), (fn) => { fire = fn; });
  t.track("landing_view");
  t.track("cta_click");
  assert.equal(t.pending(), 2);
  assert.deepEqual(seen, []);
  fire();
  await t.flush();
  assert.deepEqual(seen, ["landing_view", "cta_click"]);
  t.track("after");
  assert.deepEqual(seen, ["landing_view", "cta_click", "after"]);
});

test("loader runs once", async () => {
  let loads = 0;
  const t = createTracker(async () => { loads++; return { capture() {} }; }, () => {});
  await Promise.all([t.flush(), t.flush()]);
  assert.equal(loads, 1);
});
