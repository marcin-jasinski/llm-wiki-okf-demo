# Task: build xWiki backend (MCP client)

Labels: wayfinder:task
Status: ready-for-agent
Blocked-by: 02-storage-abstraction-design, 03-xwiki-instance, 05-remote-review-gate, 06-okf-on-xwiki-mapping
Map: ../MAP.md

## Question

Implement the remote storage backend: agent as MCP client to the xWiki MCP server chosen in the landscape research (including building the thin REST-wrapping MCP server if that was the recommendation), honoring the decided abstraction, OKF-on-xWiki mapping, and remote review gate. Backend switch via config; smoke tests for backend switching (xWiki live or mocked per the abstraction ADR).
