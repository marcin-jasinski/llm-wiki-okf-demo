# Task: replace file_answer tool with an automatic y/n prompt after query answers

Labels: wayfinder:task
Status: closed (2026-07-13)
Map: ../MAP.md

## Question

ADR 0006 keeps filing a Query answer human-*triggered* — but today that means the user has to know to say "file that" in natural language, and the LLM decides whether to call the `file_answer` Router tool. Per the grilling session: replace this with a deterministic REPL-level `y/n` prompt shown right after every `query_wiki` answer. `y`/`yes` files it (auto-slugified path/title from the question, no further prompt); anything else (including a blank line) skips it. Scope: query answers only — ingest/lint already write to the wiki as part of their own job. Remove the `file_answer` Router tool entirely; one path to file an answer, not two.

## Comments

**Resolution:** `Router` tracks `last_question` alongside `last_answer` and sets `awaiting_save = True` whenever `query_wiki` is dispatched (reset at the top of `handle()`). Added `Router.file_last_answer()` — deterministic, same `okf.wrap_frontmatter` write as before, path `wiki/query-answers/<slug>.md` slugified from the question. Removed `file_answer` from `ROUTER_TOOLS`/`ROUTER_PROMPT`/`_dispatch`. `repl.py` checks `router.awaiting_save` after printing the answer and prompts `Save this answer to the wiki? [y/n]: `. Tests updated in `tests/test_router.py` (old `file_answer`-tool tests replaced with direct `file_last_answer()`/`awaiting_save` tests); `tests/test_repl.py` covers the y/n prompt wiring.

Recorded as ADR 0014 (amends ADR 0006).
