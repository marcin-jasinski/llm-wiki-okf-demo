# Task: build xWiki backend (MCP client)

Labels: wayfinder:task
Status: ready-for-agent
Blocked-by: 02-storage-abstraction-design, 03-xwiki-instance, 05-remote-review-gate, 06-okf-on-xwiki-mapping
Map: ../MAP.md

## Question

Implement the remote storage backend: build the thin xWiki MCP server (Python `mcp` SDK, stdio, httpx over xWiki REST — see the [landscape research](../assets/01-xwiki-mcp-landscape.md) for endpoints and gotchas) and the agent-side MCP client that consumes it, honoring the decided abstraction, OKF-on-xWiki mapping, and remote review gate. Backend switch via config; smoke tests for backend switching (xWiki live or mocked per the abstraction ADR).
