# Bundle-relative `.md` links are rewritten to live xWiki URLs in storage (amends 0012)

[ADR 0015](0015-backend-aware-link-rendering.md) already rewrites links inside a *rendered
Query answer* to a page's live xWiki URL. It left links inside *stored* wiki pages alone —
`index.md`'s catalog, and cross-links between concept pages — because at the time nothing
served those pages except through the Store API. That gap is the bug here: a stored
`[Orders](/tables/orders.md)` link is rendered by xWiki as an `<a href="/tables/orders.md">`
in the actual served page, and there is no resource at that URL — xWiki pages are served at
`/bin/view/<space>/.../<name>`, with no `.md` suffix and no filesystem behind them. Every
stored cross-link was dead on click.

`XWikiStore.write` now rewrites each bundle-relative `.md` link (`okf.LINK_RE`, shared with
ADR 0015's rewriter) to `self.page_url(...)` before the REST `put`. `XWikiStore.read`
reverses it back to the bundle-relative `/path/page.md` form, so grep, Lint, and the Query
answer's `known`-pages check keep seeing the plain OKF link convention they already expect —
same pattern as [ADR 0016](0016-xwiki-frontmatter-rendering.md) used for frontmatter.
`LocalStore` is untouched: a `.md` link is already the correct, directly-clickable form for a
file on disk.

Links with a scheme (`://`) are left alone — an external citation URL that happens to end in
`.md` (e.g. a GitHub `README.md`) is not one of ours to rewrite; ADR 0015's regex comment
already flagged this ambiguity, and the same check resolves it here without needing a `known`
existence lookup (would cost a `walk()` REST call per write, and forward-references to
not-yet-written concepts are meant to keep working, not to be treated as errors).

This is the second narrowing of ADR 0012's "byte-for-byte" claim: round-tripping a page
through `write`/`read` now also normalizes a link's leading slash (always added back), not
just leaves frontmatter's raw bytes alone. Functionally the link is unchanged; only its exact
on-disk-if-it-were-local spelling can shift on the xWiki backend.
