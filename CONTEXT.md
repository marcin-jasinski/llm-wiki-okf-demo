# llm-wiki-okf-demo

A demo agent implementing the LLM Wiki pattern over an OKF-conformant wiki, using a tool-calling loop against OpenRouter or local LM Studio. This glossary only defines terms specific to this project's own design — it assumes familiarity with the LLM Wiki and OKF source specs for their own vocabulary (Concept, Frontmatter, Bundle, etc.).

## Language

**Wiki Directory** (`WIKI_DIR`):
The OKF-conformant bundle — concept pages, `index.md`, `log.md` — that the agent reads and writes. Configured independently of the Raw Sources Directory; they typically live side by side in one git repo the user manages, but nothing requires that. The agent itself never runs git.
_Avoid_: database, knowledge base, vault, wiki repo

**Raw Sources Directory** (`RAW_SOURCES_DIR`):
Where immutable input documents live — dropped in locally or fetched via URL. Read-only to the agent (enforced by the file-primitive sandbox, not just convention); the background watcher polls it for new files to Ingest.
_Avoid_: uploads, inbox, raw/ (no longer a fixed subfolder name — it's its own configured path)

**Operation**:
One of the agent's three high-level capabilities — Ingest, Query, Lint. Exposed uniformly as callable tools to both the Router and the MCP server, so every entry point shares identical behavior.
_Avoid_: command, mode

**Router**:
The top-level tool-calling loop behind the interactive REPL. Its only tools are the three Operations — it interprets the user's natural language and decides which Operation to invoke. Distinct from the inner tool loop each Operation runs over the file primitives (read_file/write_file/list_dir/grep/fetch_url).
_Avoid_: dispatcher, orchestrator

**Wiki Conventions doc** (`AGENTS.md`):
An optional file at the Wiki Repo root, supplied by whoever owns that repo, appended to the agent's baked-in system prompt to add domain-specific guidance (preferred concept types, tag taxonomy, etc). Realizes the LLM Wiki spec's "schema" layer.
_Avoid_: schema — OKF already reserves "Schema" for the `# Schema` body heading (an asset's columns/fields); reusing it for this file would collide with that meaning.

**Self-Healing Lint**:
The Lint Operation's behavior of directly writing fixes for structural issues (orphan pages, missing cross-references, unlinked mentioned concepts) instead of only reporting them. Deliberately excludes content-judgment fixes (contradictions, staleness) — those stay undetected/unfixed by this Operation.
_Avoid_: auto-fix, health-check
