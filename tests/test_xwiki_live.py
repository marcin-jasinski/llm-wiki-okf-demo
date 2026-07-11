"""Live end-to-end test: real xWiki MCP server + REST round-trip (ticket 09).

Skips unless a demo xWiki is reachable (docker compose up + setup_xwiki.py).
Exercises the full stack — XWikiStore -> MCPPageClient -> stdio MCP server ->
xWiki REST — against a throwaway space it cleans up.
"""

import os
import uuid

import httpx
import pytest

from wikiagent.store import XWikiStore
from wikiagent.xwiki_client import make_page_client

BASE_URL = os.getenv("XWIKI_BASE_URL", "http://localhost:8080")
CFG = {
    "base_url": BASE_URL,
    "user": os.getenv("XWIKI_USER", "superadmin"),
    "password": os.getenv("XWIKI_PASSWORD", "xwiki-demo"),
    "wiki": os.getenv("XWIKI_WIKI", "xwiki"),
}


def _xwiki_up() -> bool:
    try:
        return httpx.get(f"{BASE_URL}/rest", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _xwiki_up(),
                                reason="no live xWiki at XWIKI_BASE_URL")


def test_store_round_trips_through_real_xwiki():
    space = f"WikiTest{uuid.uuid4().hex[:8]}"  # throwaway, unique per run
    client = make_page_client({**CFG, "space": space})
    store = XWikiStore(client, space=space)
    page = "---\ntype: concept\ntitle: Ledger\n---\n\nSee [x](tables/orders.md).\n"
    try:
        store.write("concepts/ledger.md", page)
        assert store.read("concepts/ledger.md") == page  # verbatim markdown/1.2
        assert store.walk() == ["concepts/ledger.md"]
        assert store.list() == ["concepts/"]
        assert store.list("concepts") == ["ledger.md"]
    finally:
        client.delete([space, "concepts"], "ledger")
        client._s.close()
