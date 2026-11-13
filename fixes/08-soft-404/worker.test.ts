import { test } from "node:test";
import assert from "node:assert/strict";
import worker, { classify, compile, isKnownRoute } from "./worker.ts";

const env = {
  ASSETS: {
    async fetch(req: Request | string) {
      const u = new URL(typeof req === "string" ? req : req.url);
      if (u.pathname === "/index.html") return new Response("<html>shell</html>", { headers: { "content-type": "text/html" } });
      if (u.pathname === "/assets/app.js") return new Response("js");
      return new Response("not found", { status: 404 });
    },
  },
};

const get = (p: string) => worker.fetch(new Request("https://joinpond.ai" + p), env);

test("the seven missing pages and a random path return 404 with the SPA shell", async () => {
  for (const p of ["/docs", "/pricing", "/catalog", "/help", "/marketplace", "/changelog", "/status", "/nope"]) {
    const r = await get(p);
    assert.equal(r.status, 404, p);
    assert.equal(await r.text(), "<html>shell</html>");
  }
});

test("real routes, including params, return 200", async () => {
  for (const p of ["/", "/login", "/workflows/pw_1058be43f6482ca64fa86b7d", "/brain/team/t1/settings"]) {
    assert.equal((await get(p)).status, 200, p);
  }
});

test("static files pass through to assets", async () => {
  assert.equal((await get("/assets/app.js")).status, 200);
  assert.equal((await get("/assets/missing.js")).status, 404);
});

test("classify", () => {
  assert.equal(classify("/mcp"), "backend");
  assert.equal(classify("/favicon.svg"), "static");
  assert.equal(classify("/workflows"), "page");
  assert.equal(classify("/workflows/a/b"), "missing");
});

test("param segments need a value", () => {
  const m = compile(["/workflow/:solutionId"]);
  assert.equal(isKnownRoute("/workflow/x", m), true);
  assert.equal(isKnownRoute("/workflow", m), false);
});
