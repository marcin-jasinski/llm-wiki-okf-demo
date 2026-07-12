"""The five sandboxed file primitives — the LLM's uniform tool surface (ADR 0011).

Virtual paths route to two trees: "wiki/..." goes through the Wiki Store
(pluggable), "sources/..." reads the local Raw Sources Directory. Writes
are only ever allowed under wiki/ — the sandbox rule from the README,
enforced here rather than by convention.
"""

import re
from pathlib import Path

import httpx


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
            self._check_log_append_only(content)
        self.store.write(rel, content)
        return f"wrote {path}"

    def _check_log_append_only(self, new_content: str) -> None:
        """log.md is append-only (OKF spec §7): every existing entry must still
        appear, in order, in the new content — writes can add lines, never
        drop or rewrite them."""
        try:
            old_content = self.store.read("log.md")
        except (FileNotFoundError, OSError):
            return
        old_lines = [ln for ln in old_content.splitlines() if ln.strip()]
        new_lines = iter(ln for ln in new_content.splitlines() if ln.strip())
        for old_line in old_lines:
            if not any(new_line == old_line for new_line in new_lines):
                raise SandboxError(
                    "log.md is append-only: this write drops or alters an "
                    f"existing entry: {old_line[:100]!r}")

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
