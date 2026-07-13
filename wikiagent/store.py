"""Wiki Store: the pluggable storage seam behind the file primitives (ADR 0011).

Paths are bundle-relative POSIX strings ("tables/orders.md"). The xWiki store
implements this same interface over MCP, mapping each path to an xWiki page per
ADR 0012.
"""

from pathlib import Path
from typing import List, Optional, Protocol
from urllib.parse import quote


class LocalStore:
    """Wiki Store over a local directory (WIKI_DIR)."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _abs(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"path escapes the wiki: {rel}")
        return p

    def read(self, rel: str) -> str:
        return self._abs(rel).read_text(encoding="utf-8")

    def write(self, rel: str, content: str) -> None:
        p = self._abs(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def list(self, rel: str = "") -> list[str]:
        """One directory level: file names, subdirectories with a '/' suffix."""
        entries = []
        for child in sorted(self._abs(rel).iterdir()):
            entries.append(child.name + "/" if child.is_dir() else child.name)
        return entries

    def walk(self) -> List[str]:  # typing.List: the list() method shadows the builtin here
        """All file paths in the store, bundle-relative."""
        return sorted(
            p.relative_to(self.root).as_posix()
            for p in self.root.rglob("*")
            if p.is_file()
        )

    def page_url(self, rel: str) -> Optional[str]:
        """No live URL for a page on disk — the answer renderer renders it locally instead."""
        return None


class PageClient(Protocol):
    """The generic xWiki page operations XWikiStore drives (over MCP).

    Injecting this is the test seam: real code passes the MCP-backed client
    (xwiki_client.make_page_client), tests pass an in-memory fake.
    """

    def get(self, spaces: list[str], name: str) -> Optional[str]: ...
    def put(self, spaces: list[str], name: str, content: str) -> None: ...
    def delete(self, spaces: list[str], name: str) -> None: ...
    def list_all(self, spaces: list[str]) -> list[tuple[list[str], str]]: ...


class XWikiStore:
    """Wiki Store over an xWiki space, via a page-level MCP client (ADR 0011).

    OKF↔page mapping (ADR 0012): a bundle-relative "a/b/c.md" is the terminal
    page `c` under nested spaces [root, a, b]; content is stored verbatim.
    """

    def __init__(self, client: PageClient, space: str, base_url: str = ""):
        self.client = client
        self.space = space
        self.base_url = base_url.rstrip("/")

    def page_url(self, rel: str) -> Optional[str]:
        """Live xWiki view URL for a page (ADR 0012's path<->space mapping, ADR 0015)."""
        spaces, name = self._to_ref(rel)
        return self.base_url + "/bin/view/" + "/".join(
            quote(part, safe="") for part in [*spaces, name])

    def _to_ref(self, rel: str) -> tuple[list[str], str]:
        rel = rel.replace("\\", "/").strip("/")
        if not rel.endswith(".md"):
            raise ValueError(f"xWiki store holds .md pages only: {rel}")
        *dirs, fname = rel.split("/")
        return [self.space, *dirs], fname.removesuffix(".md")

    def _from_ref(self, spaces: list[str], name: str) -> str:
        return "/".join([*spaces[1:], name]) + ".md"  # spaces[0] is the root space

    def read(self, rel: str) -> str:
        # ponytail: no per-Operation content cache yet (ADR 0011 §grep names one);
        # O(pages) REST GETs is fine at demo scale, add a write-invalidated cache
        # if a real bundle makes grep slow.
        spaces, name = self._to_ref(rel)
        content = self.client.get(spaces, name)
        if content is None:
            raise FileNotFoundError(rel)
        return content

    def write(self, rel: str, content: str) -> None:
        spaces, name = self._to_ref(rel)
        self.client.put(spaces, name, content)

    def walk(self) -> List[str]:
        return sorted(self._from_ref(sp, name)
                      for sp, name in self.client.list_all([self.space]))

    def list(self, rel: str = "") -> list[str]:
        """One level, matching LocalStore: names, subdirs with a '/' suffix."""
        prefix = rel.replace("\\", "/").strip("/")
        prefix = prefix + "/" if prefix else ""
        is_dir: dict[str, bool] = {}
        for p in self.walk():
            if not p.startswith(prefix):
                continue
            head, sep, _ = p[len(prefix):].partition("/")
            is_dir[head] = bool(sep) or is_dir.get(head, False)
        # sort by bare name, then suffix dirs — LocalStore sorts before appending '/'
        return [h + "/" if is_dir[h] else h for h in sorted(is_dir)]


def make_store(wiki_backend: str, *, wiki_dir=None, xwiki=None):
    if wiki_backend == "local":
        return LocalStore(wiki_dir)
    if wiki_backend == "xwiki":
        from wikiagent.xwiki_client import make_page_client
        return XWikiStore(make_page_client(xwiki), xwiki["space"],
                          base_url=xwiki.get("base_url", ""))
    raise ValueError(f"unknown WIKI_BACKEND: {wiki_backend!r} (expected local|xwiki)")
