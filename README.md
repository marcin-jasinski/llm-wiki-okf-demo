# llm-wiki-okf-demo

AI agent that maintains an OKF-conformant wiki using the LLM Wiki pattern.
This repo is the agent only — the wiki it works on (sources + pages) lives in a separate git repo or directory you point it at.

Runs against OpenRouter or a local LM Studio model, interchangeably, via a single OpenAI-compatible client.

## The idea in one paragraph

Every page the agent writes is a valid OKF concept document (frontmatter + `type`, `index.md`/`log.md`, cross-links) — so this demo isn't "LLM Wiki" and "OKF" as two separate things, it's OKF as the wire format for an LLM-Wiki-maintained knowledge base.

## Three Operations

The agent has exactly three high-level capabilities, uniformly available from every interface:

- **Ingest** — read a local file or fetch a URL, integrate it into the wiki (new/updated concept pages, updated `index.md`, appended `log.md` entry).
- **Query** — answer a question by reading the wiki, render the answer as a styled HTML page opened in your browser. Read-only — never writes anything on its own.
- **Lint** — self-heal structural issues: orphan pages, missing cross-references, concepts mentioned but not yet documented. Writes fixes directly, but only structural ones — no content judgment calls (contradictions, staleness) are auto-resolved. See [`docs/adr/0007`](docs/adr/0007-structural-only-lint.md).

Each Operation runs its own inner tool-calling loop over five sandboxed file primitives (`read_file`, `write_file`, `list_dir`, `grep`, `fetch_url`). `write_file` is only ever allowed inside `WIKI_DIR` — the Raw Sources Directory is read-only to the agent, enforcing the "raw sources are immutable" rule from the LLM Wiki spec at the tool level, not just by convention.

## How you run it

One entry point:

```
uv run main.py
```

This starts:
- a **background watcher**, polling `RAW_SOURCES_DIR` — drop a new source file in and it gets ingested automatically;
- a **foreground REPL** — talk to it in plain language ("how do I do X?", "ingest it", "lint the wiki") and the agent (the *Router*) figures out which Operation to call. See [`docs/adr/0008`](docs/adr/0008-single-process-router.md).

For external MCP hosts (Claude Desktop, Claude Code, etc.) the same three operations are also available as an MCP server, run separately:

```
uv run mcp_server.py
```

## Configuration

Copy `.env.example` to `.env`:

```
WIKI_DIR=/path/to/wiki-repo/wiki
RAW_SOURCES_DIR=/path/to/wiki-repo/raw
LLM_BACKEND=openrouter          # or: lmstudio
OPENROUTER_API_KEY=sk-...
MODEL_NAME=...
LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

`WIKI_DIR` and `RAW_SOURCES_DIR` are configured separately — they typically live side by side inside one git repo you've cloned locally, but nothing requires that. This repo never runs `git` on your behalf — after Ingest or Lint writes files, you review `git diff` and commit by hand. See [`docs/adr/0004`](docs/adr/0004-git-stays-manual.md).

If `WIKI_DIR` has an `AGENTS.md` at its root, the agent reads it and folds it into its system prompt as domain-specific guidance on top of the baked-in OKF conventions.

## Design docs

- [`CONTEXT.md`](CONTEXT.md) — glossary of this project's own vocabulary
- [`docs/adr/`](docs/adr/) — architectural decisions and why
