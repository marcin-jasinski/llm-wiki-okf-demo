# xWiki-stored frontmatter is fenced as a ```yaml block (amends 0012)

xWiki's `markdown/1.2` syntax is CommonMark: a bare `---` line at the top of a document
becomes a thematic break (`<hr>`), and a `---` line directly under a preceding text line
becomes a setext heading underline instead. OKF frontmatter is exactly that shape — a
`---`-delimited YAML block — so on the xWiki backend it rendered as a stray horizontal
rule followed by the `title:`/`type:` line turned into a heading, not as metadata. Local
Markdown viewers (Obsidian, VS Code, static-site generators) special-case the
leading-`---` convention and render it as a metadata panel, so the same bytes look fine
there — the two backends just need different bytes on the wire to look right.

`XWikiStore.write` (`wikiagent/store.py`) now rewrites a leading `---\n...\n---\n`
frontmatter block into a fenced `` ```yaml\n...\n``` `` block before the REST `put`;
`XWikiStore.read` reverses it on the way back out. Every other layer (`okf.parse_frontmatter`,
grep, lint, the local mirror renderer) only ever calls `Store.read`/`write`, so from their
view content is still the plain `---` form, unchanged from before this ADR — `LocalStore`
is untouched, and `okf.wrap_frontmatter`'s output round-trips through `XWikiStore` exactly
as `test_read_round_trips_verbatim` already asserted.

This narrows [ADR 0012](0012-okf-on-xwiki-mapping.md)'s "byte-for-byte, nothing is
rewritten" claim: it now holds through the `Store` API (round-trip via `read`/`write`),
not for the raw bytes sitting in the xWiki REST payload. Exporting a bundle by walking
`store.read()` over every page is still byte-identical to the original — only a raw REST
dump of the space would show the fenced form.

Rejected installing an xWiki frontmatter-aware rendering extension (e.g. a Jekyll-style
front-matter macro): needs an extra extension in `docker/setup_xwiki.py`, not guaranteed
to exist for `markdown/1.2`, and is more moving parts than a five-line, fully-reversible
text substitution at the one seam (`XWikiStore`) ADR 0011 already designates for
backend-specific divergence — the same pattern ADR 0015 used for link rendering.
