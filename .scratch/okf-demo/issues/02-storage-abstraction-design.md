# Grilling: storage abstraction design

Labels: wayfinder:grilling
Status: closed (2026-07-10)
Assignee: Marcin (claimed 2026-07-10)
Blocked-by: 01-xwiki-mcp-landscape
Map: ../MAP.md

## Question

What interface do the three Operations see over pluggable storage? Do the five file primitives (`read_file`, `write_file`, `list_dir`, `grep`, `fetch_url`) stay the tool surface with a remote implementation behind them, or does the backend interface differ (e.g. `grep` becomes xWiki search; `fetch_url` stays backend-independent)? How is the backend selected (`.env` `STORAGE_BACKEND=local|xwiki`?) and is it fixed per session? How does the write sandbox rule ("writes only inside WIKI_DIR") translate to xWiki (writes only inside one space?)? Outcome: a decided interface + config story, recorded as an ADR.

## Comments

**Resolution (2026-07-10):** Decided in a grilling session; recorded as [ADR 0011 — Pluggable Wiki Store behind an unchanged five-primitive tool surface](../../../docs/adr/0011-pluggable-wiki-store.md), with new glossary terms **Wiki Store** and **xWiki MCP Server** in `CONTEXT.md`. Gist: the five primitives stay the LLM's tool surface on both backends; a `WikiStore` interface behind them swaps local disk for an MCP client to our auto-spawned, stdio, page-CRUD xWiki MCP server; grep on xWiki is client-side regex (exact semantics, demo-scale ceiling); selection via `WIKI_BACKEND=local|xwiki`; sandbox rule becomes "put_page only inside XWIKI_SPACE", enforced in the primitive layer.
