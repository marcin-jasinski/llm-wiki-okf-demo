"""Clear demo/sources/ and demo/wiki/ back to empty (docs/demo.md).

Both are gitignored working state: demo/sources/ is what the watcher/Ingest
consumes, demo/wiki/ is what Ingest generates (local backend only — for xWiki
use scripts/reset_xwiki.py instead). Run before a demo to discard whatever a
prior run left behind. Seeding demo/sources/ from the tracked
demo/sources.baseline/ (the canonical 5 starting documents) is a separate,
explicit step done when starting the demo — see docs/demo.md.

Both directories are cleared in place (contents removed, directory itself
kept) rather than deleted and recreated — the background watcher holds a
handle on demo/sources/, and deleting it out from under a running watcher
breaks the watch.

Run:  uv run scripts/reset_sources.py
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCES = ROOT / "demo" / "sources"
WIKI = ROOT / "demo" / "wiki"


def _clear(dir_path: Path) -> None:
    """Empty dir_path in place, creating it if missing."""
    dir_path.mkdir(parents=True, exist_ok=True)
    for child in dir_path.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()


def main() -> None:
    _clear(SOURCES)
    print("cleared demo/sources/")

    _clear(WIKI)
    print("cleared demo/wiki/")


if __name__ == "__main__":
    main()
