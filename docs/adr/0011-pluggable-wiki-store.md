# Pluggable Wiki Store behind an unchanged five-primitive tool surface

The wiki's storage is pluggable — local disk (`WIKI_DIR`) or a self-hosted xWiki — but the LLM never sees the difference: every Operation exposes the same five file primitives (`read_file`, `write_file`, `list_dir`, `grep`, `fetch_url`) on both backends, and the swap happens behind a `WikiStore` interface those primitives call. Selection is `WIKI_BACKEND=local|xwiki` in `.env`, fixed for the process lifetime. Rejected giving the LLM backend-native tools (`get_page`/`put_page`/search on xWiki): it would fork every Operation prompt and double the prompt-engineering and testing surface for no demo benefit.

The xWiki store is an MCP client to our own thin xWiki MCP server — built by us because research found no viable existing one (the official `application-ai-llm-mcp` exposes search only, no page CRUD; community servers are immature). The server exposes generic page-level tools (`get_page`, `put_page`, `list_pages`, `delete_page`) over stdio and is auto-spawned as a subprocess when `WIKI_BACKEND=xwiki`, keeping it a reusable, agent-agnostic xWiki MCP server rather than an OKF-demo-specific one.

Two consequences of keeping the surface uniform:

- **`grep` on xWiki runs client-side**: the store lists pages in the space, fetches content (cached per Operation run), and applies the regex locally — exact grep semantics on both backends. Rejected mapping grep to Solr search, which would silently degrade regex patterns to keyword queries per backend. Ceiling: O(pages) fetches; fine at demo scale, swap to a Solr-shortlist hybrid if it ever matters.
- **The write sandbox translates symmetrically**: "`write_file` only inside `WIKI_DIR`" becomes "`put_page` only inside `XWIKI_SPACE`" (configured alongside `XWIKI_BASE_URL`/`XWIKI_USER`/`XWIKI_PASSWORD`), enforced in the primitive layer exactly like the local path check. Raw sources and the watcher stay local-disk on both backends.
