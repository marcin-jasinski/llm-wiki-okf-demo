# Research: xWiki MCP server landscape

Labels: wayfinder:research
Status: closed (2026-07-10)
Assignee: Marcin (claimed 2026-07-10)
Blocked-by: —
Map: ../MAP.md

## Question

Does a viable, maintained MCP server for xWiki exist? Survey the landscape: official/community xWiki MCP servers, what tools they expose (get/put/list/search pages? attachments? spaces?), auth model, transport (STDIO/HTTP), install story, and maturity. Also assess Plan B: how complete is xWiki's REST API for page CRUD + search, and how much work is a thin custom MCP server wrapping it (Python `mcp` SDK). Deliverable: a markdown summary linked from this ticket, with a clear recommendation (use server X / build thin wrapper).

## Comments

**Resolution (2026-07-10):** Full findings in [the research summary](../assets/01-xwiki-mcp-landscape.md). Verdict: **build the thin wrapper** — the official XWiki MCP server (`application-ai-llm-mcp`, actively maintained) exposes only `search_wiki`/`list_collections` with no page CRUD and requires the LLM Application + vector index; the three community servers (npm/TS, Node demo, unlicensed Python) are all 0–4 stars and absent from the MCP registry. Plan B is solid: xWiki's REST API fully covers page CRUD (`/wikis/{w}/spaces/{s}/pages/{p}`, JSON via `?media=json`), Solr search, spaces/pages listing, and attachments; auth is HTTP Basic (no core token mechanism). Pages accept a `syntax` element — `markdown/1.2` works when the CommonMark Markdown Syntax 1.2 extension (`syntax-markdown-commonmark12`) is installed; probe via `/rest/syntaxes`. Wrapper estimate: ~150–250 lines, `mcp` Python SDK high-level server + `@mcp.tool()`, stdio transport, httpx. Gotchas recorded: XML body on PUT to set syntax, nested spaces as repeated `/spaces/{name}` segments, 1000-item paging cap.
