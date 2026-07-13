"""Single interactive entry point (ADR 0008): background watcher over the
Raw Sources Directory + foreground Router REPL, one process, `uv run main.py`.
"""

import sys
import threading
import time
from pathlib import Path

from wikiagent.config import build
from wikiagent.router import Router

POLL_INTERVAL = 3.0  # seconds
PROMPT = "\n> "
SAVE_PROMPT = "\nSave this answer to the wiki? [y/n]: "

# Single-writer (the REPL thread), read by the watcher thread: whichever input()
# the REPL is currently blocked on, so a watcher report reprints the right one
# instead of always claiming the main "> " prompt is what's waiting for input.
_current_prompt = PROMPT


def new_files(sources_dir, seen: set) -> list[str]:
    """Relative paths of files under sources_dir not in `seen` (watcher poll)."""
    current = {p.relative_to(sources_dir).as_posix()
               for p in Path(sources_dir).rglob("*") if p.is_file()}
    return sorted(current - seen)


def report_ingest(router: Router, rel_path: str) -> None:
    """Print a watcher ingest report, then reprint the prompt.

    The watcher runs on a background thread while the foreground input() is
    blocked waiting on the user — printing the report alone leaves no visible
    prompt underneath it, so every report ends by redrawing one.
    """
    print(f"\n[watcher] new source detected: {rel_path} — ingesting…")
    print(f"[watcher] {router.run_ingest(f'sources/{rel_path}')}")
    print(_current_prompt, end="", flush=True)


def watch(router: Router, sources_dir, stop: threading.Event):
    seen = set(new_files(sources_dir, set()))  # pre-existing files are not re-ingested
    while not stop.wait(POLL_INTERVAL):
        for f in new_files(sources_dir, seen):
            seen.add(f)
            report_ingest(router, f)


def maybe_prompt_save(router: Router) -> None:
    """After a query_wiki answer, ask y/n to file it (ADR 0014)."""
    global _current_prompt
    if not router.awaiting_save:
        return
    _current_prompt = SAVE_PROMPT
    try:
        answer = input(SAVE_PROMPT.lstrip("\n")).strip().lower()
    finally:
        _current_prompt = PROMPT
    if answer in ("y", "yes"):
        print(router.file_last_answer())


def main():
    # Windows consoles default to a legacy code page (e.g. cp1250); LLM output
    # can carry characters outside it (✓, —, emoji). Print as UTF-8, replacing
    # the rare un-encodable glyph rather than crashing the REPL mid-demo.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    settings, client, prims, ops = build()
    router = Router(ops, prims, client, model=settings.model)
    stop = threading.Event()
    threading.Thread(target=watch, args=(router, settings.raw_sources_dir, stop),
                     daemon=True).start()
    print(f"llm-wiki-okf-demo — wiki: {settings.wiki_backend}, "
          f"llm: {settings.llm_backend}/{settings.model}")
    print("Talk to the wiki agent (Ctrl-C or 'exit' to quit).")
    try:
        while True:
            text = input(PROMPT).strip()
            if not text:
                continue
            if text.lower() in ("exit", "quit"):
                break
            print(router.handle(text))
            maybe_prompt_save(router)
    except (KeyboardInterrupt, EOFError):
        pass
    stop.set()


if __name__ == "__main__":
    main()
