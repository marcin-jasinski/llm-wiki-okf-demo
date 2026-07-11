"""MCP-backed page client: the sync↔async bridge to our xWiki MCP server.

XWikiStore (sync, ADR 0011) drives page CRUD through this. We auto-spawn the
xWiki MCP server (wikiagent.xwiki_mcp_server) as a stdio subprocess and keep one
long-lived MCP session, so grep — which reads every page — reuses one connection
rather than re-launching Python per call.

The whole session lifecycle lives inside a single coroutine (`_serve`) on a
background event loop; sync methods submit `call_tool` coroutines to that loop.
This is deliberate: mcp's stdio context managers are cancel-scope-bound to the
task that entered them, so entering/exiting them anywhere but their own task
raises. call_tool from another task is fine — it's just message I/O.

ponytail: one persistent stdio session on a worker thread. If a demo ever needs
concurrency, give each caller its own session; not worth it at demo scale.
"""

import asyncio
import json
import os
import sys
import threading
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class _StdioSession:
    """A persistent MCP stdio session running on its own event loop thread."""

    def __init__(self, params: StdioServerParameters):
        self._loop = asyncio.new_event_loop()
        self._session: Optional[ClientSession] = None
        self._ready = threading.Event()
        self._stop: Optional[asyncio.Event] = None
        self._error: Optional[BaseException] = None
        threading.Thread(target=self._run, args=(params,), daemon=True).start()
        self._ready.wait(timeout=60)
        if self._session is None:
            raise RuntimeError(f"xWiki MCP server failed to start: {self._error}")

    def _run(self, params):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve(params))
        except BaseException as e:  # surface startup failures to __init__
            self._error = e
            self._ready.set()

    async def _serve(self, params):
        self._stop = asyncio.Event()
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                self._ready.set()
                await self._stop.wait()

    def call(self, tool: str, args: dict) -> str:
        """Call a tool, blocking until it returns; yields concatenated text."""
        assert self._session is not None  # __init__ blocks until it's set
        fut = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(tool, args), self._loop)
        result = fut.result()
        text = "".join(getattr(c, "text", "") for c in result.content)
        if result.isError:
            raise RuntimeError(f"xWiki MCP tool {tool} failed: {text}")
        return text

    def close(self):
        if self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)


class MCPPageClient:
    """PageClient backed by the xWiki MCP server (satisfies store.PageClient)."""

    def __init__(self, session: _StdioSession):
        self._s = session

    def get(self, spaces: list[str], name: str) -> Optional[str]:
        r = json.loads(self._s.call("get_page", {"spaces": spaces, "name": name}))
        return r["content"] if r["exists"] else None

    def put(self, spaces: list[str], name: str, content: str) -> None:
        self._s.call("put_page", {"spaces": spaces, "name": name, "content": content})

    def delete(self, spaces: list[str], name: str) -> None:
        self._s.call("delete_page", {"spaces": spaces, "name": name})

    def list_all(self, spaces: list[str]) -> list[tuple[list[str], str]]:
        refs = json.loads(self._s.call("list_pages", {"spaces": spaces}))
        return [(r["spaces"], r["name"]) for r in refs]


def make_page_client(xwiki: dict) -> MCPPageClient:
    """Spawn the xWiki MCP server and return a page client over it.

    `xwiki` carries base_url/user/password/wiki; they reach the server as env.
    """
    env = {**os.environ,
           "XWIKI_BASE_URL": xwiki["base_url"],
           "XWIKI_USER": xwiki["user"],
           "XWIKI_PASSWORD": xwiki["password"],
           "XWIKI_WIKI": xwiki.get("wiki", "xwiki")}
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "wikiagent.xwiki_mcp_server"], env=env)
    return MCPPageClient(_StdioSession(params))
