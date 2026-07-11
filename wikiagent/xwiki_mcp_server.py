"""Thin, agent-agnostic xWiki MCP server (ticket 09, ADR 0011).

Four generic page-level tools over xWiki's REST API, stdio transport. No OKF
knowledge lives here — it wraps xWiki page CRUD + subtree listing so any MCP
client can drive an xWiki. The OKF↔page mapping (ADR 0012) is the client's job
(see wikiagent.store.XWikiStore).

Config from env (the store passes these when it spawns us):
  XWIKI_BASE_URL   e.g. http://localhost:8080   (REST root is <base>/rest)
  XWIKI_USER, XWIKI_PASSWORD                     HTTP Basic auth
  XWIKI_WIKI       wiki name, default "xwiki"

Run standalone:  python -m wikiagent.xwiki_mcp_server

References use an explicit space list + terminal page name, so nested spaces
and dotted names need no escaping games (landscape research gotcha #2).
"""

import json
import os
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("XWIKI_BASE_URL", "http://localhost:8080").rstrip("/")
WIKI = os.environ.get("XWIKI_WIKI", "xwiki")
AUTH = (os.environ.get("XWIKI_USER", ""), os.environ.get("XWIKI_PASSWORD", ""))
SYNTAX = "markdown/1.2"

PAGE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<page xmlns="http://www.xwiki.org">'
    "<title>{title}</title><syntax>{syntax}</syntax><content>{content}</content>"
    "</page>"
)

mcp = FastMCP("xwiki")


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _space_path(spaces: list[str]) -> str:
    """[A, B] -> '/spaces/A/spaces/B' with each segment URL-encoded."""
    return "".join(f"/spaces/{quote(s, safe='')}" for s in spaces)


def _page_url(spaces: list[str], name: str) -> str:
    return f"{BASE_URL}/rest/wikis/{WIKI}{_space_path(spaces)}/pages/{quote(name, safe='')}"


@mcp.tool()
def get_page(spaces: list[str], name: str) -> str:
    """Fetch one page's markdown content. Returns JSON {"exists", "content"}."""
    r = httpx.get(f"{_page_url(spaces, name)}?media=json", auth=AUTH, timeout=30)
    if r.status_code == 404:
        return json.dumps({"exists": False, "content": ""})
    r.raise_for_status()
    return json.dumps({"exists": True, "content": r.json().get("content", "")})


@mcp.tool()
def put_page(spaces: list[str], name: str, content: str) -> str:
    """Create or update a page, storing content verbatim as markdown/1.2."""
    xml = PAGE_XML.format(title=_xml_escape(name), syntax=SYNTAX,
                          content=_xml_escape(content))
    r = httpx.put(_page_url(spaces, name), auth=AUTH, content=xml,
                  headers={"Content-Type": "application/xml"}, timeout=60)
    r.raise_for_status()
    return "created" if r.status_code == 201 else "updated"


@mcp.tool()
def delete_page(spaces: list[str], name: str) -> str:
    """Delete a page. Idempotent: a missing page is reported, not an error."""
    r = httpx.delete(_page_url(spaces, name), auth=AUTH, timeout=60)
    if r.status_code == 404:
        return "absent"
    r.raise_for_status()
    return "deleted"


@mcp.tool()
def list_pages(spaces: list[str]) -> str:
    """All terminal pages in the space subtree rooted at `spaces`.

    Returns JSON list of {"spaces": [...], "name": ...}. Uses the wiki-wide
    pages endpoint filtered by the root space: unlike per-space /spaces
    listing, it reports pages in nested spaces that have no WebHome (which is
    every OKF page we write — ADR 0012). Skips WebHome; demo scale, one page.
    """
    root = ".".join(spaces)  # ponytail: dotted ref; OKF slugs have no dots
    r = httpx.get(f"{BASE_URL}/rest/wikis/{WIKI}/pages",
                  params={"space": root, "number": 1000, "media": "json"},
                  auth=AUTH, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json().get("pageSummaries", []):
        ref = p.get("space", "")
        if ref != root and not ref.startswith(root + "."):
            continue  # ?space= prefix-matches; keep only our subtree
        if p.get("name") == "WebHome":
            continue
        out.append({"spaces": ref.split("."), "name": p["name"]})
    return json.dumps(out)


if __name__ == "__main__":
    mcp.run()
