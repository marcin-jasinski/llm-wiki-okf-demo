"""Wiki Store: the pluggable storage seam behind the file primitives (ADR 0011).

Paths are bundle-relative POSIX strings ("tables/orders.md"). The xWiki
store (ticket 09) implements this same interface over MCP.
"""

from pathlib import Path
from typing import List


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


def make_store(backend: str, *, wiki_dir=None, **kwargs):
    if backend == "local":
        return LocalStore(wiki_dir)
    if backend == "xwiki":
        raise NotImplementedError("xWiki store lands with ticket 09")
    raise ValueError(f"unknown WIKI_BACKEND: {backend!r} (expected local|xwiki)")
