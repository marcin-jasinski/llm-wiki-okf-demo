# OKF bundle maps onto xWiki as verbatim markdown pages

An OKF v0.1 bundle maps onto the xWiki space `XWIKI_SPACE` by storing each `.md` file **byte-for-byte as page content** in the `markdown/1.2` syntax. YAML frontmatter, body, and bundle-relative links all live in-band in the page content exactly as they appear on disk — nothing is lifted out into xWiki object properties, and no link rewriting happens.

Path ↔ page reference is mechanical: a bundle-relative path's directory components become nested spaces and its filename (minus `.md`) becomes the terminal page name, all under the bundle root space `XWIKI_SPACE`.

```
tables/orders.md  ->  spaces=[XWIKI_SPACE, "tables"], page="orders"
index.md          ->  spaces=[XWIKI_SPACE],          page="index"
```

The reserved bundle files `index.md`/`log.md` are ordinary terminal pages named `index`/`log` in the root space (not xWiki `WebHome` documents) — keeping the mapping uniform for every file and avoiding a special case. Enumeration skips any `WebHome` page, which we never write.

**Conformance is by construction**: exporting the space is "walk every page under `XWIKI_SPACE`, write its content to `<path>.md`", and because content is stored unchanged the result is byte-identical to the original bundle. An OKF conformance check (`okf.check_bundle`) passes on the export with no reassembly step.

Rejected lifting frontmatter into xWiki object properties and translating bundle-relative links to native `[[page]]` links: it would fork the uniform primitive surface ADR 0011 fixed, demand bidirectional translation on every read and write, and make export a reassembly job instead of a copy — more code and more failure modes for a "more native" feel the demo never surfaces (Query and Lint read page content through the Wiki Store, not xWiki's rendered HTML). Scope is the demo; `markdown/1.2` round-trips verbatim (verified in ticket 03), so the simplest mapping is also the conformant one.
