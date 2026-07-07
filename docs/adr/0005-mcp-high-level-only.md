# MCP server exposes only high-level Operations, never file primitives

The MCP server exposes exactly the three Operations (`ingest_source`, `query_wiki`, `lint_wiki`) — never `read_file`/`write_file`/etc. Exposing file primitives directly would let an external MCP host's own model (e.g. whatever Claude Desktop is configured with) do the actual wiki-maintenance reasoning, silently bypassing the OpenRouter/LM Studio backend this demo exists to showcase. Keeping Operations as the only surface means every entry point — REPL, background watcher, MCP host — always runs the same configured brain.
