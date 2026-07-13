# Task: make links inside rendered query answers actually work

Labels: wayfinder:task
Status: closed (2026-07-13)
Map: ../MAP.md

## Question

`Operations.query` renders the answer markdown straight to a one-off temp HTML file and opens it via `file://`. The system prompt tells the LLM to write cross-links as bundle-relative `[title](/path/page.md)` — the wiki's *internal* link convention — which is meaningless once opened as a standalone `file://` page: it resolves against the filesystem root and points at raw `.md`. On the xWiki backend there's no local file at all, so no `file://` link could ever be correct.

Per the grilling session: local backend renders the *entire* wiki bundle to a temp HTML mirror on every query (multi-hop links must keep working, not just the first hop from the answer); xWiki backend rewrites links to the page's live `bin/view` URL instead of rendering anything locally. The seam is per-`Store` (ADR 0011: "Store is the one place local/remote diverge").

## Comments

**Resolution:** Added `Store.page_url(rel) -> str | None`: `LocalStore` always returns `None` (render locally instead); `XWikiStore` returns the real `XWIKI_BASE_URL/bin/view/<nested spaces>/<page>` URL (needed threading `base_url` into `XWikiStore.__init__` and `make_store`). Rewrote `agent.render_answer_html(answer_md, store)`: renders every `store.walk()` page whose `page_url()` is `None` to a sibling temp HTML file (absolute `file://` URIs for cross-links, sidesteps relative-path math), and rewrites the answer's own links the same way. When every page has a `page_url()` (xWiki), no local rendering happens at all — links go straight to xWiki. Links to pages absent from `store.walk()` (not-yet-written concepts, allowed by the OKF convention) keep their original bundle-relative href — still inert once rendered, same as before this change, rather than rewritten to a *new* dead href. Tests: `tests/test_agent.py` (local multi-hop rendering, xwiki live-URL rewriting via a fake store), `tests/test_store.py` (`page_url` on both stores).

Recorded as ADR 0015.

**Follow-up from code review:** duplicated per-page render logic (markdown render + template + write) between the bundle loop and the answer itself, extracted to `_render_page()`. Added a `ponytail:` comment on the whole-bundle-per-query re-render naming its ceiling (O(pages) per query; cache by write-version if a real bundle ever makes it slow). Fixed inaccurate wording here and in ADR 0015 about not-yet-written links being "left as text" — they're left with their original, already-inert href, still a real (if dead) anchor once rendered; strengthened the corresponding test to assert the exact unrewritten `href=` rather than substring presence.
