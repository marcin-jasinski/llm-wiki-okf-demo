"""The six sandboxed file primitives — the LLM's uniform tool surface (ADR 0011).

Virtual paths route to two trees: "wiki/..." goes through the Wiki Store
(pluggable), "sources/..." reads the local Raw Sources Directory. Writes
are only ever allowed under wiki/ — the sandbox rule from the README,
enforced here rather than by convention.
"""

import re
from datetime import datetime
from pathlib import Path

import httpx

from wikiagent.okf import LINK_RE, clean_frontmatter


class SandboxError(Exception):
    pass


def _split(path: str) -> tuple[str, str]:
    """Validate a virtual path and split into (root, relpath)."""
    path = path.replace("\\", "/").strip("/")
    parts = path.split("/")
    root, rel_parts = parts[0], parts[1:]
    if root not in ("wiki", "sources"):
        raise SandboxError(f"path must start with wiki/ or sources/: {path}")
    if any(p in ("..", "") for p in rel_parts) or ":" in path:
        raise SandboxError(f"illegal path: {path}")
    return root, "/".join(rel_parts)


class Primitives:
    def __init__(self, store, sources_dir: Path):
        self.store = store
        self.sources_dir = Path(sources_dir).resolve()

    def read_file(self, path: str) -> str:
        root, rel = _split(path)
        if root == "wiki":
            return self.store.read(rel)
        return (self.sources_dir / rel).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        root, rel = _split(path)
        if root != "wiki" or not rel:
            raise SandboxError("write_file is only allowed inside wiki/")
        if rel == "AGENTS.md":
            raise SandboxError("wiki/AGENTS.md is read-only (wiki-conventions doc)")
        if rel == "log.md":
            raise SandboxError("wiki/log.md is append-only — use the append_log tool")
        if rel == "index.md":
            self._check_index_keeps_links(content)
        self.store.write(rel, clean_frontmatter(content))
        return f"wrote {path}"

    def _check_index_keeps_links(self, new_content: str) -> None:
        """index.md is the catalog (OKF): every page it already links to must
        still be linked after a write. Entries may be reworded/reorganized
        freely — only silently dropping an existing catalog entry is rejected,
        which is what an ingest that forgets to merge in the prior index looks
        like (each run overwriting index.md with only its own new entry)."""
        try:
            old_content = self.store.read("index.md")
        except (FileNotFoundError, OSError):
            return
        dropped = set(LINK_RE.findall(old_content)) - set(LINK_RE.findall(new_content))
        if dropped:
            raise SandboxError(
                "wiki/index.md must keep every existing catalog entry: this write "
                f"drops the link(s) to {sorted(dropped)}. Read the current index.md "
                "and add to its entries instead of replacing them.")

    def append_log(self, message: str) -> str:
        """Append one timestamped entry to wiki/log.md at the bottom (OKF spec
        §7: append-only). Formatting and placement are deterministic — the LLM
        only supplies the message text. Entries are blank-line-separated, not
        just newline-separated: Markdown (incl. xWiki's CommonMark renderer)
        treats a single '\\n' as a soft break that collapses into the same
        line — a blank line forces each entry onto its own rendered line."""
        entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] - {message}"
        try:
            old = self.store.read("log.md").rstrip("\n")
        except (FileNotFoundError, OSError):
            old = ""
        new_content = f"{old}\n\n{entry}\n" if old else f"{entry}\n"
        self.store.write("log.md", new_content)
        return f"appended to wiki/log.md: {entry}"

    def list_dir(self, path: str) -> list[str]:
        root, rel = _split(path)
        if root == "wiki":
            return self.store.list(rel)
        base = self.sources_dir / rel
        return sorted(c.name + "/" if c.is_dir() else c.name for c in base.iterdir())

    def grep(self, pattern: str, root: str = "wiki") -> list[str]:
        """Regex search; returns "root/path:lineno:line" hits."""
        rx = re.compile(pattern)
        if root == "wiki":
            files = [(f"wiki/{p}", lambda p=p: self.store.read(p)) for p in self.store.walk()]
        elif root == "sources":
            files = [
                (f"sources/{p.relative_to(self.sources_dir).as_posix()}",
                 lambda p=p: p.read_text(encoding="utf-8"))
                for p in sorted(self.sources_dir.rglob("*")) if p.is_file()
            ]
        else:
            raise SandboxError(f"grep root must be wiki or sources: {root}")
        hits = []
        for name, load in files:
            try:
                text = load()
            except UnicodeDecodeError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{name}:{i}:{line}")
        return hits

    def fetch_url(self, url: str) -> str:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        return resp.text
