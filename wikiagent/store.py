"""Wiki Store: the pluggable storage seam behind the file primitives (ADR 0011).

Paths are bundle-relative POSIX strings ("tables/orders.md"). The xWiki store
implements this same interface over MCP, mapping each path to an xWiki page per
ADR 0012.
"""

import re
from pathlib import Path
from typing import List, Optional, Protocol
from urllib.parse import quote, unquote

from wikiagent.okf import LINK_RE

_ANY_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def _to_xwiki_markdown(text: str) -> str:
    """Fence OKF `---` frontmatter as a ```yaml code block (ADR 0016): xWiki's
    CommonMark renderer otherwise turns a bare `---` into a <hr>/setext heading
    instead of showing it as metadata. Reversed by `_from_xwiki_markdown` on
    read, so every other layer still sees plain `---` frontmatter."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    fm, body = text[4:end + 1], text[end + 5:]
    return f"```yaml\n{fm}```\n{body}"


def _from_xwiki_markdown(text: str) -> str:
    """Inverse of `_to_xwiki_markdown`."""
    if not text.startswith("```yaml\n"):
        return text
    end = text.find("\n```\n", 8)
    if end == -1:
        return text
    fm, body = text[8:end + 1], text[end + 5:]
    return f"---\n{fm}---\n{body}"


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
        return self._rewrite_links_in(_from_xwiki_markdown(content))

    def write(self, rel: str, content: str) -> None:
        spaces, name = self._to_ref(rel)
        content = self._rewrite_links_out(_to_xwiki_markdown(content))
        self.client.put(spaces, name, content)

    def _rewrite_links_out(self, content: str) -> str:
        """Point a bundle-relative `.md` cross-link at the target's live xWiki
        URL (ADR 0017): a raw '.md' href has nothing to resolve against once
        xWiki serves the page, so links break. Reversed by `_rewrite_links_in`
        on read, so every other layer still sees plain bundle-relative links.
        Leaves alone anything with a scheme ("://") — an external citation
        link that happens to end in .md, not one of ours."""
        def repl(m: re.Match) -> str:
            href = m.group(1)
            if "://" in href:
                return m.group(0)
            return f"]({self.page_url(href)})"
        return LINK_RE.sub(repl, content)

    def _rewrite_links_in(self, content: str) -> str:
        """Inverse of `_rewrite_links_out`."""
        prefix = self.base_url + "/bin/view/" + quote(self.space, safe="") + "/"
        def repl(m: re.Match) -> str:
            href = m.group(1)
            if not href.startswith(prefix):
                return m.group(0)
            path = "/".join(unquote(part) for part in href[len(prefix):].split("/"))
            return f"](/{path}.md)"
        return _ANY_LINK_RE.sub(repl, content)

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
