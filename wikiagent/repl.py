"""Single interactive entry point (ADR 0008): background watcher over the
Raw Sources Directory + foreground Router REPL, one process, `uv run main.py`.
"""

import threading
import time

from wikiagent.config import build
from wikiagent.router import Router, new_files

POLL_INTERVAL = 3.0  # seconds


def watch(router: Router, sources_dir, stop: threading.Event):
    seen = set(new_files(sources_dir, set()))  # pre-existing files are not re-ingested
    while not stop.wait(POLL_INTERVAL):
        for f in new_files(sources_dir, seen):
            seen.add(f)
            print(f"\n[watcher] new source detected: {f} — ingesting…")
            print(f"[watcher] {router.run_ingest(f'sources/{f}')}")


def main():
    settings, client, prims, ops = build()
    router = Router(ops, prims, client, model=settings.model_name)
    stop = threading.Event()
    threading.Thread(target=watch, args=(router, settings.raw_sources_dir, stop),
                     daemon=True).start()
    print(f"llm-wiki-okf-demo — wiki: {settings.wiki_backend}, "
          f"llm: {settings.llm_backend}/{settings.model_name}")
    print("Talk to the wiki agent (Ctrl-C or 'exit' to quit).")
    try:
        while True:
            text = input("\n> ").strip()
            if not text:
                continue
            if text.lower() in ("exit", "quit"):
                break
            print(router.handle(text))
    except (KeyboardInterrupt, EOFError):
        pass
    stop.set()


if __name__ == "__main__":
    main()
