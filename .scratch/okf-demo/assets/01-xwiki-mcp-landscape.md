# XWiki MCP server landscape (researched 2026-07-10)

Investigated against primary sources: xwiki.org documentation, extensions.xwiki.org, GitHub repos and GitHub API metadata, the official MCP registry (registry.modelcontextprotocol.io), the modelcontextprotocol/servers repo, npm registry, and PyPI. All claims cite their source URL.

## Summary

- **An official XWiki MCP server exists** (part of the xwiki-contrib LLM Application, streamable HTTP, actively maintained), **but it is search-only**: two tools (`search_wiki`, `list_collections`), no page CRUD. It also requires installing the LLM Application + its vector index inside XWiki. Source: [xwiki.org MCP Server doc](https://www.xwiki.org/xwiki/bin/view/documentation/extensions/user/llm/mcp-server).
- **No mature community MCP server with full page CRUD exists.** The best candidate, `vitos73/xwiki-mcp` (npm `xwiki-mcp` 0.2.0, stdio, Solr search + create/delete page), has 4 stars, 3 commits, and was last pushed 2026-06-03. Two other repos are one-day or student-grade projects. None appear in the official MCP registry or in `modelcontextprotocol/servers`.
- **XWiki's REST API is fully sufficient for a thin wrapper**: page GET/PUT/DELETE, space/page listing, Solr search, and attachments are all documented endpoints; JSON output is available via `?media=json`. Auth is HTTP Basic (no built-in API tokens in core).
- **Markdown pages are supported**: a page's `<syntax>` field is settable via PUT, and the CommonMark `markdown/1.2` syntax is provided by the installable `syntax-markdown-commonmark12` extension (v8.9, LGPL 2.1).
- **Recommendation: build the thin custom MCP wrapper** (Python `mcp` SDK, ~4 tools, roughly a day of work) rather than depend on any existing server.

## Existing MCP servers

Searches run: web search `xwiki MCP "Model Context Protocol"`; `site:extensions.xwiki.org MCP`; GitHub repo search `xwiki mcp` (4 hits total); GitHub org search `org:xwiki-contrib mcp` / `llm`; npm registry search `xwiki mcp`; PyPI package probes `xwiki-mcp`, `mcp-xwiki`, `xwiki-mcp-server` (all 404); official MCP registry `GET /v0/servers?search=xwiki` (0 results); `modelcontextprotocol/servers` README (no XWiki or any wiki entry).

### 1. Official: XWiki "MCP Server" extension (LLM Application, xwiki-contrib/ai-llm)

- **What it is**: A module (`application-ai-llm-mcp`) of the xwiki-contrib **LLM project**, which "aims to integrate artificial intelligence in the form of Large Language Models (LLMs) into the XWiki platform". Source repo: [github.com/xwiki-contrib/ai-llm](https://github.com/xwiki-contrib/ai-llm) (Java 94.8%, 455 commits, 21 releases, last push 2026-07-07 per GitHub; requires XWiki 16.2.0+).
- **Tools exposed** (verbatim from the official doc): only two —
  - `search_wiki` — "Search the wiki using semantic and keyword similarity. Returns the most relevant content chunks from indexed pages." Params: `query` (required), `collections`, `limitKeywordResults` (default 10), `limitSemanticResults` (default 10). Returns XML-like `<result>` text chunks.
  - `list_collections` — lists searchable collections, one id per line.
  - **No page create/read/update/delete, no attachments, no space listing.** It searches the *LLM index* (vector + keyword), not raw pages: "The MCP server can be used to give an LLM-based agent access to data that is indexed in the index for the LLM application."
- **Transport**: "The MCP server needs to be configured as 'HTTP' or streamable HTTP (without SSE) server", URL `https://<server>/<context>/rest/wikis/<wiki>/aiLLM/mcp`.
- **Auth**: "The MCP uses XWiki's configured authentication method(s). By default, it doesn't ask for authentication" (guest-accessible collections work anonymously); a basic-auth `Authorization` header works; with the OpenID Connect Provider extension installed, guests are denied and MCP clients get an OIDC token flow.
- **Install story**: Java extension installed *inside* XWiki via Extension Manager. Notably, per the doc FAQ: "the MCP server currently isn't installed as a dependency of any other extension of the LLM extension and needs to be installed explicitly." It also requires the LLM Application + Index (embedding-based) to have content to search.
- **Maturity/license**: LLM project last version 0.9, license LGPL 2.1, extension page last modified 2026-07-08 ([extensions.xwiki.org/…/Extension/LLM/](https://extensions.xwiki.org/xwiki/bin/view/Extension/LLM/)); the MCP doc page was last modified 2026-05-12. Active but pre-1.0.
- Doc source: [www.xwiki.org/xwiki/bin/view/documentation/extensions/user/llm/mcp-server](https://www.xwiki.org/xwiki/bin/view/documentation/extensions/user/llm/mcp-server)

### 2. Community: vitos73/xwiki-mcp (npm `xwiki-mcp`)

- **Repo**: [github.com/vitos73/xwiki-mcp](https://github.com/vitos73/xwiki-mcp) — TypeScript, MIT. GitHub API: created 2026-03-13, last push 2026-06-03, 4 stars, 2 open issues.
- **Tools** (from README): read — `search`, `list_spaces`, `list_pages`, `get_page`, `get_page_children`, `get_attachments`; write (v0.2+) — `create_page`, `delete_page`, `add_comment`. **No update-in-place tool listed and no attachment upload.** Search is Solr-backed full text, with a "legacy" HQL fallback that "searches page names only".
- **Auth**: env vars, three modes — `basic` (`XWIKI_USERNAME`/`XWIKI_PASSWORD`), `token` (Bearer via `XWIKI_TOKEN`), `none`.
- **Transport**: stdio.
- **Install**: `npm install -g xwiki-mcp` or `npx xwiki-mcp`. Published to npm: latest **0.2.0**, published 2026-06-03 ([registry.npmjs.org/xwiki-mcp](https://registry.npmjs.org/xwiki-mcp)).
- **Maturity**: 3 commits, no GitHub releases, 4 stars, single maintainer. Decent README (config examples, search syntax guide). Not listed in the official MCP registry.

### 3. Community: alfredfs85/xwiki-mcp-server

- **Repo**: [github.com/alfredfs85/xwiki-mcp-server](https://github.com/alfredfs85/xwiki-mcp-server) — JavaScript/Node.js 20+, MIT, 4 stars. GitHub API: created **and** last pushed 2026-02-20 (a one-day project, untouched since).
- **Tools** (from README): `search_xwiki`, `get_xwiki_page`, `create_xwiki_page` — no update, delete, spaces, or attachments.
- **Auth**: basic auth via `XWIKI_USERNAME`/`XWIKI_PASSWORD` env vars.
- **Transport**: HTTP with SSE alternative (runs as a standalone Node/Docker process).
- **Maturity**: effectively abandoned demo; default search limit 10; no releases.

### 4. Community: germanKoch/xwiki-mcp

- **Repo**: [github.com/germanKoch/xwiki-mcp](https://github.com/germanKoch/xwiki-mcp) — Python 3.12+/uv, **no license**, 0 stars. GitHub API: created 2026-04-22, last push 2026-04-29.
- **Tools** (from README): `search_pages`, `get_page`, `list_spaces`, `list_pages`, `create_or_update_page` (writes XWiki 2.1 markup), `replace_text`. Stdio transport, basic auth via env vars, run via `uvx`.
- **Maturity**: closest tool surface to what a thin wrapper needs, but zero adoption, no license (legally unusable as a dependency), one week of activity. Not on PyPI.

### Registry results (negative)

- Official MCP registry: `https://registry.modelcontextprotocol.io/v0/servers?search=xwiki` returns `{"servers":[],"metadata":{"count":0}}` (checked 2026-07-10).
- [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) README: no XWiki entry; no wiki-platform entries at all in the reference list.
- PyPI: `xwiki-mcp`, `mcp-xwiki`, `xwiki-mcp-server` all 404 — **no Python package exists**.
- extensions.xwiki.org: the only MCP-related extension is the official one under the LLM project above.

## XWiki REST API assessment

Source for everything in this section: [XWiki RESTful API documentation](https://www.xwiki.org/xwiki/bin/view/Documentation/UserGuide/Features/XWikiRESTfulAPI) (fetched 2026-07-10).

- **Entry point**: `https://<host>:<port>/<context>/rest` (context is `xwiki` or empty for the root/Docker install).
- **Formats**: XML by default (XSD-defined). **JSON is available everywhere** via `?media=json` or `Accept: application/json` — the doc's own example: `curl -H 'Accept: application/json' https://www.xwiki.org/xwiki/rest/`.
- **Page CRUD** at `/wikis/{wikiName}/spaces/{spaceName}[/spaces/{nestedSpaceName}]*/pages/{pageName}`:
  - `GET` — page element; optional query params `objects`, `class`, `attachments`, `prettyNames`.
  - `PUT` — "Create or updates a page." Accepts `application/xml` (Page element), `text/plain` (content only), or `application/x-www-form-urlencoded` (fields `title`, `parent`, `hidden`, `content`). Returns 201 created / 202 updated / 304 not modified. Partial update is supported: "You can specify a subset of the three elements title, syntax, and content".
  - `DELETE` — 204 on success; `skipRecycleBin` param since 18.6.0.
- **Syntax / Markdown**: the Page XML representation includes a `<syntax>` element (doc example: `<syntax>xwiki/2.0</syntax>`) that can be sent on PUT, and `GET /rest/syntaxes` returns "The list of syntaxes supported by the XWiki instance." So a page can be created *and stored* in Markdown by setting `<syntax>markdown/1.2</syntax>` — **provided the Markdown syntax extension is installed**. The `markdown/1.2` syntax id is provided by the **CommonMark Markdown Syntax 1.2** extension (`org.xwiki.contrib.markdown:syntax-markdown-commonmark12`, current v8.9, LGPL 2.1, installable via Extension Manager, CommonMark 0.28 flavor + wikilink/table/strikethrough extensions): [extensions.xwiki.org/…/Extension/Markdown Syntax 1.2/](https://extensions.xwiki.org/xwiki/bin/view/Extension/Markdown%20Syntax%201.2/). Content is returned in whatever syntax the page is stored in; since 18.2.0 a `supportedSyntax` GET param can additionally return an HTML rendering when the stored syntax isn't in the client's list.
- **Search**:
  - `/wikis/{wikiName}/search?q={keywords}[&scope={name,content,title,objects}]` — keyword search; since **17.5.0 backed by Solr by default** (configurable via `rest.keywordSearchSource`).
  - `/wikis/{wikiName}/query?q={query}&type={hql,xwql,lucene,solr}` — raw query endpoint; since 17.10.5/18.2.0 "By default, only the solr query type is available" (others need `rest.allowedQueryTypes`).
  - `/wikis/query?q=...&wikis=...` — multi-wiki Solr search.
- **Listing**: `/wikis/{w}/spaces` (spaces), `/wikis/{w}/spaces/{s}/pages` (pages in a space), `/wikis/{w}/pages?name=&space=&author=` (filtered wiki-wide page list), `/wikis/{w}/children` (16.4.0+, top-level pages), page `/children` with `hierarchy=nestedpages`. Paged responses cap at **1000 items** per request (400 error if a higher limit is requested).
- **Attachments**: `GET/PUT/DELETE /wikis/{w}/spaces/{s}/pages/{p}/attachments/{attachmentName}` — full attachment CRUD, plus space- and wiki-level attachment listing/search.
- **Auth**: three documented mechanisms — **HTTP Basic** (`Authorization` header), **XWiki session cookies**, and **custom authenticators** ("such as OIDC, or Trusted authentication"). Unauthenticated requests run as `XWiki.Guest`. **There is no built-in personal-access-token / API-token mechanism in core XWiki** — token-style auth requires an extension (e.g., the OIDC Provider, or the LLM project's "token-based authentication" module mentioned on the [LLM extension page](https://extensions.xwiki.org/xwiki/bin/view/Extension/LLM/)).
- **CSRF gotcha**: since 14.10.8/15.2, `POST` with `text/plain`, `multipart/form-data`, or `application/x-www-form-urlencoded` requires the `XWiki-Form-Token` header (obtainable from any prior response; 403 "Invalid or missing form token." otherwise). PUT with `application/xml` — the path a wrapper would use — is not listed as requiring it.

## Thin-wrapper effort estimate

Using the official Python SDK ([github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk), PyPI package `mcp`):

- **SDK primitives**: the high-level server class (named `MCPServer` in the current README; historically `FastMCP` — older docs/examples use `from mcp.server.fastmcp import FastMCP`) with the `@mcp.tool()` decorator — type hints + docstrings generate the tool schemas, "no JSON Schema, no request parsing, no validation code". Supports stdio, streamable HTTP, and SSE transports; stdio is all a local demo needs.
- **Tool surface** (~4-6 tools, one HTTP call each via `httpx`):
  - `get_page(space, page)` → GET page with `?media=json`
  - `put_page(space, page, title, content, syntax)` → PUT XML Page element (title/syntax/content) — also covers create
  - `delete_page(space, page)` → DELETE
  - `search(query)` → GET `/wikis/{w}/query?q=...&type=solr&media=json`
  - optionally `list_spaces()` / `list_pages(space)`
- **Gotchas** (all verified against the REST doc above):
  1. **XML on PUT**: the clean way to set page *syntax* (needed for Markdown pages) is the XML Page representation — the form-urlencoded variant only carries `title`/`parent`/`hidden`/`content`. Responses can be JSON (`?media=json`), so only the PUT body needs XML (a 5-line template string).
  2. **Nested spaces**: each nesting level is a separate `/spaces/{name}` path segment (`/spaces/A/spaces/B/pages/C`), and segment names need URL-encoding. The tool API should take a list or dotted reference and expand it.
  3. **Markdown**: `syntax: markdown/1.2` only works if `syntax-markdown-commonmark12` is installed in the XWiki instance; probe `GET /rest/syntaxes` at startup or on first failure.
  4. **Auth**: basic auth only (httpx `auth=` parameter); credentials via env vars.
  5. **Search fallback**: on older XWiki (<17.5.0) the `/search` endpoint is HQL/database-backed name-and-title matching; prefer `/query?type=solr`.
  6. Result paging caps at 1000 items; irrelevant for a demo.
- **Effort**: roughly **150-250 lines / half a day to a day** including manual testing against a live instance. This matches what the three community projects each did solo in days.

## Recommendation

**Build the thin custom MCP wrapper over the XWiki REST API.** The official XWiki MCP server is search-only (no page CRUD) and drags in the whole LLM Application + embedding index — wrong tool for an agent that must write pages. Every community server is a low-single-digit-stars, single-maintainer project (the best, `xwiki-mcp` on npm, has 3 commits and lacks a page-update tool; the only Python one is unlicensed), so depending on any of them carries more risk than the ~200 lines they each wrap. The REST API covers everything needed — page GET/PUT/DELETE with a settable `markdown/1.2` syntax, Solr search, JSON responses — and the Python `mcp` SDK reduces the server itself to a handful of decorated functions.

## Sources

- Official XWiki MCP Server doc: https://www.xwiki.org/xwiki/bin/view/documentation/extensions/user/llm/mcp-server (page last modified 2026-05-12)
- XWiki RESTful API documentation: https://www.xwiki.org/xwiki/bin/view/Documentation/UserGuide/Features/XWikiRESTfulAPI
- LLM extension page (versions, LGPL 2.1 license): https://extensions.xwiki.org/xwiki/bin/view/Extension/LLM/
- CommonMark Markdown Syntax 1.2 extension: https://extensions.xwiki.org/xwiki/bin/view/Extension/Markdown%20Syntax%201.2/
- xwiki-contrib LLM repo (contains `application-ai-llm-mcp`): https://github.com/xwiki-contrib/ai-llm
- vitos73/xwiki-mcp: https://github.com/vitos73/xwiki-mcp — npm: https://registry.npmjs.org/xwiki-mcp
- alfredfs85/xwiki-mcp-server: https://github.com/alfredfs85/xwiki-mcp-server
- germanKoch/xwiki-mcp: https://github.com/germanKoch/xwiki-mcp
- Official MCP registry query (0 results): https://registry.modelcontextprotocol.io/v0/servers?search=xwiki
- MCP reference servers list (no XWiki entry): https://github.com/modelcontextprotocol/servers
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- GitHub API metadata (stars, push dates): https://api.github.com/repos/vitos73/xwiki-mcp, https://api.github.com/repos/alfredfs85/xwiki-mcp-server, https://api.github.com/repos/germanKoch/xwiki-mcp
