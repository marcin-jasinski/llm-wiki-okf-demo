# llm-wiki-okf-demo

AI agent that maintains an OKF-conformant wiki using the LLM Wiki pattern.
This repo is the agent only — the wiki it works on (sources + pages) lives in a separate git repo or directory you point it at.

Runs against OpenRouter or a local LM Studio model, interchangeably, via a single OpenAI-compatible client. The wiki's storage is likewise pluggable — local disk or a self-hosted xWiki — behind an unchanged tool surface (see [Storage backends](#storage-backends)).

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
MODEL_NAME=...                  # model used on the openrouter backend
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=...              # model used on the lmstudio backend

WIKI_BACKEND=local              # or: xwiki (see Storage backends)
```

`WIKI_DIR` and `RAW_SOURCES_DIR` are configured separately, and **must not overlap** — they typically live side by side inside one git repo you've cloned locally (e.g. `repo/wiki` and `repo/raw`), but nothing requires that. On the local backend this repo never runs `git` on your behalf — after Ingest or Lint writes files, you review `git diff` and commit by hand. See [`docs/adr/0004`](docs/adr/0004-git-stays-manual.md).

## Storage backends

The wiki lives behind a pluggable Wiki Store, selected by `WIKI_BACKEND` and fixed for the process (ADR [`0011`](docs/adr/0011-pluggable-wiki-store.md)). The LLM never sees which is active — the same five file primitives work on both:

- **`local`** — the OKF bundle is plain files under `WIKI_DIR`.
- **`xwiki`** — the bundle lives in a self-hosted xWiki space. The agent auto-spawns a thin xWiki MCP server (over stdio, wrapping xWiki's REST API) and stores each page as verbatim `markdown/1.2`, so exporting the space reproduces a conformant OKF bundle byte-for-byte (ADR [`0012`](docs/adr/0012-okf-on-xwiki-mapping.md)). Extra config:

  ```
  WIKI_BACKEND=xwiki
  XWIKI_BASE_URL=http://localhost:8080
  XWIKI_USER=superadmin
  XWIKI_PASSWORD=...
  XWIKI_SPACE=WikiDemo          # the write sandbox — writes never escape it
  ```

  Stand up a local demo xWiki with `docker/docker-compose.yml` + `docker/setup_xwiki.py`. There's no `git diff` gate on xWiki: writes are gated by ingest approval (ADR [`0006`](docs/adr/0006-human-gated-ingest.md)) and audited/rolled back via xWiki's native page history (ADR [`0013`](docs/adr/0013-remote-review-gate.md)).

If `WIKI_DIR` has an `AGENTS.md` at its root, the agent reads it and folds it into its system prompt as domain-specific guidance on top of the baked-in OKF conventions.

## Try it

[`docs/demo.md`](docs/demo.md) is a scripted walkthrough — ingest → query → lint over a fictional SaaS company's docs (`demo/sources/`), first on the local backend, then the same beats on xWiki with a one-line `.env` change.

## Design docs

- [`docs/demo.md`](docs/demo.md) — the end-to-end demo walkthrough
- [`CONTEXT.md`](CONTEXT.md) — glossary of this project's own vocabulary
- [`docs/adr/`](docs/adr/) — architectural decisions and why
