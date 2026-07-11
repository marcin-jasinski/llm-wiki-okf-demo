"""Restore demo/sources/ to the clean baseline (docs/demo.md).

demo/sources/ is regenerated working state (gitignored, like demo/wiki/);
demo/sources.baseline/ is the tracked canonical copy of the 5 starting
documents. Run before a demo to discard whatever a prior Ingest/watcher run
left behind, plus any extra file dropped in for a later beat (e.g. the Ledger
doc in demo/sources.baseline.extra/).

Run:  uv run scripts/reset_sources.py
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCES = ROOT / "demo" / "sources"
BASELINE = ROOT / "demo" / "sources.baseline"


def main() -> None:
    if SOURCES.exists():
        shutil.rmtree(SOURCES)
    shutil.copytree(BASELINE, SOURCES)
    count = len(list(BASELINE.glob("*.md")))
    print(f"reset demo/sources/ to the {count} baseline document(s)")


if __name__ == "__main__":
    main()
