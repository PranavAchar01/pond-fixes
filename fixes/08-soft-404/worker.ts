// Cloudflare Worker in front of the Vite SPA. Known routes get index.html
// with 200; unknown paths get the same index.html with 404, so the SPA still
// renders its not-found page but crawlers, monitors and agents see the truth.
import routes from "./routes.json" with { type: "json" };

interface Env {
  ASSETS: { fetch(req: Request | string): Promise<Response> };
}

const STATIC_PREFIXES = ["/assets/", "/images/", "/fonts/", "/pondflow/"];
const BACKEND_PREFIXES = ["/mcp", "/api/", "/auth/"];

type Matcher = (segs: string[]) => boolean;

export function compile(patterns: string[]): Matcher[] {
  return patterns.map((p) => {
    const want = p.split("/").filter(Boolean);
    return (segs: string[]) =>
      segs.length === want.length &&
      want.every((w, i) => w.startsWith(":") ? segs[i].length > 0 : w === segs[i]);
  });
}

const MATCHERS = compile(routes as string[]);

export function isKnownRoute(pathname: string, matchers: Matcher[] = MATCHERS): boolean {
  const segs = decodeURIComponent(pathname).split("/").filter(Boolean);
  return matchers.some((m) => m(segs));
}

export function classify(pathname: string): "static" | "backend" | "page" | "missing" {
  if (BACKEND_PREFIXES.some((p) => pathname === p.replace(/\/$/, "") || pathname.startsWith(p))) return "backend";
  if (STATIC_PREFIXES.some((p) => pathname.startsWith(p)) || /\.[a-z0-9]{1,8}$/i.test(pathname)) return "static";
  return isKnownRoute(pathname) ? "page" : "missing";
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const kind = classify(url.pathname);
    if (kind === "backend") return fetch(request);
    if (kind === "static") return env.ASSETS.fetch(request);
    const shell = await env.ASSETS.fetch(new URL("/index.html", url).toString());
    const headers = new Headers(shell.headers);
    headers.set("cache-control", "no-cache");
    return new Response(shell.body, { status: kind === "page" ? 200 : 404, headers });
  },
};
