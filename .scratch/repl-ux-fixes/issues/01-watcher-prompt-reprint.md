# Task: reprint the REPL prompt after background watcher output

Labels: wayfinder:task
Status: closed (2026-07-13)
Map: ../MAP.md

## Question

`wikiagent/repl.py`'s `watch()` thread prints `[watcher] ...` lines asynchronously while the foreground `input()` call is blocked waiting on the user, with no prompt reissued afterward — the user is left looking at output with no visible `> ` to type into. Fix: after the watcher reports an ingest, reprint the prompt so one is always visible.

## Comments

**Resolution:** Extracted `report_ingest(router, rel_path)` from `watch()`'s loop body — prints the two `[watcher]` lines then reprints the currently-active prompt. Tested directly with `capsys` (no threading needed): `tests/test_repl.py::test_report_ingest_reprints_prompt`.

**Follow-up from code review:** a watcher report firing while the *y/n save* prompt (ticket 02) is the one actually blocked on `input()` was reprinting the generic `"> "` — misleading, since the pending input is really a y/n answer. Fixed by tracking `_current_prompt` (module-level, single-writer: the REPL thread) so `report_ingest` reprints whichever prompt is genuinely active. See `tests/test_repl.py::test_report_ingest_reprints_whichever_prompt_is_currently_active`.
