# Map: REPL UX fixes — prompt reprint, automatic answer filing, working links

Labels: wayfinder:map
Status: done (2026-07-13) — all 3 tickets closed
Children: issues/01 … issues/03

## Destination

Three independent fixes to the Router REPL (`wikiagent/repl.py`) and Query answer rendering (`wikiagent/agent.py`), chartered in a `/grill-with-docs` session:

1. The `> ` prompt must always reappear after any output, including the background watcher's asynchronous ingest reports.
2. After every `query_wiki` answer, the REPL asks `y/n` to file the answer into the wiki, replacing the old natural-language "file that answer" flow (ADR 0006's `file_answer` tool).
3. Links inside a rendered query answer (and inside every page reachable from it) must actually open something — a rendered local page or a live xWiki page — instead of a dead `file://.../page.md` link.

## Notes

- Follow-up work after the `okf-demo` map (closed 2026-07-11) — not part of that map's original scope.
- Grilled decisions (full transcript in the originating conversation):
  - Watcher fix: reprint `"\n> "` after any watcher print, don't queue/delay it.
  - Auto-file prompt: query answers only (not ingest/lint); deterministic REPL-level y/n, not routed through the LLM; replaces `file_answer` entirely; path/title auto-slugified from the question, no extra prompt.
  - Links: local backend renders the *whole* wiki bundle to a temp HTML mirror on every query (multi-hop clicking must work); xWiki backend rewrites links to live `bin/view` URLs instead of rendering anything locally. The seam is a new `Store.page_url()` method (ADR 0011's "Store is where backends diverge").
- Record two new ADRs (0014 amending 0006, 0015 new).

## Decisions so far

<!-- one line per closed ticket -->

- [Task: watcher prompt reprint](issues/01-watcher-prompt-reprint.md) — `report_ingest()` reprints whichever prompt (`PROMPT` or `SAVE_PROMPT`) is currently active via a tracked `_current_prompt`, not always the main `"> "`.
- [Task: automatic file-answer y/n prompt](issues/02-automatic-file-answer-prompt.md) — `file_answer` Router tool removed; REPL asks y/n after every `query_wiki` answer; `Router.file_last_answer()` deterministically slugifies the question into a path. Recorded as ADR 0014 (amends ADR 0006).
- [Task: backend-aware link rendering](issues/03-backend-aware-link-rendering.md) — new `Store.page_url()` seam; local backend renders the whole bundle to a temp HTML mirror per query, xWiki backend rewrites to live `bin/view` URLs. Recorded as ADR 0015.

**Map complete — all 3 tickets closed.**

## Not yet specified

- None — fully scoped by the grilling session before tickets were opened.

## Out of scope

- Anything beyond these three fixes (no new Operations, no new backends).
