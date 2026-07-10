# Task: build core agent (local backend)

Labels: wayfinder:task
Status: ready-for-agent
Blocked-by: 02-storage-abstraction-design, 07-llm-backend-credentials
Map: ../MAP.md

## Question

Build the agent per README + ADRs, local backend only: `pyproject.toml` (uv), `.env.example`, single OpenAI-compatible client (ADR 0003), five sandboxed file primitives (write only inside `WIKI_DIR`, sources read-only), the three Operation tool-loops (Ingest, read-only Query with HTML render + browser open, structural-only Lint), Router REPL + background watcher in one process (ADR 0008, with the write lock), `mcp_server.py` exposing only the three Operations (ADR 0005), `AGENTS.md` folding. Includes the smoke tests for primitives and OKF conformance of written pages. Use /tdd.
