# Task: build core agent (local backend)

Labels: wayfinder:task
Status: closed (2026-07-10)
Assignee: agent (claimed 2026-07-10)
Blocked-by: 02-storage-abstraction-design, 07-llm-backend-credentials
Map: ../MAP.md

## Question

Build the agent per README + ADRs, local backend only: `pyproject.toml` (uv), `.env.example`, single OpenAI-compatible client (ADR 0003), five sandboxed file primitives (write only inside `WIKI_DIR`, sources read-only), the three Operation tool-loops (Ingest, read-only Query with HTML render + browser open, structural-only Lint), Router REPL + background watcher in one process (ADR 0008, with the write lock), `mcp_server.py` exposing only the three Operations (ADR 0005), `AGENTS.md` folding. Includes the smoke tests for primitives and OKF conformance of written pages. Use /tdd.

## Comments

**Resolution (2026-07-10):** Built TDD-first (31 tests green, mypy clean). Layout: `wikiagent/` package (`store.py` WikiStore seam per ADR 0011, `primitives.py` sandboxed five-primitive surface, `okf.py` conformance checks + deterministic wrap-with-frontmatter, `agent.py` Operations + shared tool loop, `router.py` Router + watcher poll, `config.py` composition root, `repl.py`, `mcp_server.py`), with thin root entry scripts `main.py` / `mcp_server.py` per the README. Design notes:

- The LLM addresses both trees through virtual paths — `wiki/...` (via the pluggable store) and `sources/...` (always local, read-only); the sandbox (writes only under `wiki/`, traversal rejected) is enforced in `primitives.py`.
- Router tools = the three Operations **plus `file_answer`** — the ADR 0006 human-triggered filing of the last Query answer; the write itself is deterministic (`okf.wrap_frontmatter`), not an LLM rewrite.
- Tool-call traces print to **stderr** (stdout belongs to the MCP stdio transport).
- Tested seams (pre-agreed via the ticket): primitives sandbox, OKF conformance of written pages, Operation tool loop w/ scripted fake LLM (Query has no write tool), Router routing + `file_answer`, watcher new-file detection.
- **Not yet verified live against a real LLM** — that needs ticket 07 (credentials, ready-for-human); everything LLM-facing is tested against a scripted fake client, which ADR 0003's single-client design makes representative. Live verification lands with ticket 10's demo run.
