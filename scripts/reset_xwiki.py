"""Wipe all demo content from the xWiki space, without touching the container.

Deletes every page under XWIKI_SPACE over REST, so the instance doesn't need
re-provisioning (docker/setup_xwiki.py's superadmin config + extension
install) before each demo run — only the space this demo ever writes to.

Run:  uv run scripts/reset_xwiki.py
"""

import os
import sys
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("XWIKI_BASE_URL", "").rstrip("/")
WIKI = os.environ.get("XWIKI_WIKI", "xwiki")
SPACE = os.environ.get("XWIKI_SPACE", "")
AUTH = (os.environ.get("XWIKI_USER", ""), os.environ.get("XWIKI_PASSWORD", ""))


def list_pages(space: str) -> list[dict]:
    """All terminal pages in the space subtree (mirrors xwiki_mcp_server.list_pages)."""
    r = httpx.get(f"{BASE_URL}/rest/wikis/{WIKI}/pages",
                  params={"space": space, "number": 1000, "media": "json"},
                  auth=AUTH, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json().get("pageSummaries", []):
        ref = p.get("space", "")
        if ref != space and not ref.startswith(space + "."):
            continue  # ?space= prefix-matches; keep only our subtree
        if p.get("name") == "WebHome":
            continue
        out.append({"spaces": ref.split("."), "name": p["name"]})
    return out


def delete_page(spaces: list[str], name: str) -> None:
    path = "".join(f"/spaces/{quote(s, safe='')}" for s in spaces)
    url = f"{BASE_URL}/rest/wikis/{WIKI}{path}/pages/{quote(name, safe='')}"
    r = httpx.delete(url, auth=AUTH, timeout=30)
    if r.status_code != 404:
        r.raise_for_status()


def main() -> None:
    if not (BASE_URL and SPACE and AUTH[0]):
        sys.exit("missing XWIKI_BASE_URL / XWIKI_SPACE / XWIKI_USER in .env")
    pages = list_pages(SPACE)
    if not pages:
        print(f"{SPACE} already empty")
        return
    for p in pages:
        delete_page(p["spaces"], p["name"])
        print(f"deleted {'.'.join([*p['spaces'], p['name']])}")
    print(f"reset {len(pages)} page(s) from {SPACE}")


if __name__ == "__main__":
    main()
