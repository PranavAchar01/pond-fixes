"""Minimal Streamable HTTP MCP client for Pond.

The API key comes from the POND_API_KEY environment variable, or from the
macOS keychain (service `pond-api-key`) when the variable is unset. The key is
never printed or written to disk.

usage: pond_client.py tools                        list tools (name + description)
       pond_client.py schema NAME                  print one tool's input schema
       pond_client.py call NAME '{"json":"args"}'  call a tool, print the result
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

URL = "https://joinpond.ai/mcp"
PROTOCOL = "2025-06-18"


def api_key() -> str:
    key = os.environ.get("POND_API_KEY", "").strip()
    if key:
        return key
    return subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", "pond-api-key", "-w"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@dataclass
class Response:
    message: dict | None
    seconds: float
    status: int
    headers: dict[str, str]
    raw_bytes: int  # body bytes as received on the wire (after any compression)
    body_bytes: int  # decoded body bytes
    session_id: str | None = None


@dataclass
class PondClient:
    url: str = URL
    key: str = field(default_factory=api_key, repr=False)
    session_id: str | None = None
    _next_id: int = 1

    def post(self, payload: dict, extra_headers: dict | None = None) -> Response:
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        headers.update(extra_headers or {})
        req = urllib.request.Request(self.url, json.dumps(payload).encode(), headers)
        t0 = time.perf_counter()
        try:
            resp = urllib.request.urlopen(req, timeout=300)
            status = resp.status
        except urllib.error.HTTPError as e:
            resp, status = e, e.code
        raw = resp.read()
        dt = time.perf_counter() - t0
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        body = _decode(raw, hdrs.get("content-encoding", ""))
        text = body.decode(errors="replace")
        msg = None
        if status >= 400:
            msg = {"http_error": status, "body": text[:500]}
        elif "text/event-stream" in hdrs.get("content-type", ""):
            for line in text.splitlines():
                if line.startswith("data:"):
                    d = json.loads(line[5:].strip())
                    if d.get("id") == payload.get("id"):
                        msg = d
        elif text.strip():
            msg = json.loads(text)
        return Response(
            msg, dt, status, hdrs, len(raw), len(body), hdrs.get("mcp-session-id")
        )

    def initialize(self) -> Response:
        r = self.post(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL,
                    "capabilities": {},
                    "clientInfo": {"name": "pond-fixes", "version": "1"},
                },
            }
        )
        self.session_id = r.session_id
        self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return r

    def rpc(
        self, method: str, params: dict, extra_headers: dict | None = None
    ) -> Response:
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params,
        }
        return self.post(payload, extra_headers)

    def call(self, name: str, arguments: dict | None = None) -> Response:
        return self.rpc("tools/call", {"name": name, "arguments": arguments or {}})

    @staticmethod
    def text(r: Response) -> str:
        res = (r.message or {}).get("result") or {}
        parts = [c.get("text", "") for c in res.get("content", [])]
        if not parts and res.get("structuredContent"):
            return json.dumps(res["structuredContent"])
        return "\n".join(parts)


def _decode(raw: bytes, encoding: str) -> bytes:
    encoding = encoding.lower()
    if encoding == "gzip":
        import gzip

        return gzip.decompress(raw)
    if encoding == "br":
        import brotli  # type: ignore[import-not-found]

        return brotli.decompress(raw)
    if encoding == "zstd":
        import zstandard  # type: ignore[import-not-found]

        return zstandard.ZstdDecompressor().decompress(raw)
    return raw


def main() -> None:
    c = PondClient()
    c.initialize()
    cmd = sys.argv[1]
    if cmd in ("tools", "schema"):
        tools = c.rpc("tools/list", {}).message["result"]["tools"]
        if cmd == "tools":
            for t in tools:
                print(f"- {t['name']}: {(t.get('description') or '').strip()}\n")
        else:
            print(
                json.dumps(next(t for t in tools if t["name"] == sys.argv[2]), indent=1)
            )
    elif cmd == "call":
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        r = c.call(sys.argv[2], args)
        print(f"# {r.seconds:.1f}s")
        print(PondClient.text(r) or json.dumps(r.message, indent=1))


if __name__ == "__main__":
    main()
