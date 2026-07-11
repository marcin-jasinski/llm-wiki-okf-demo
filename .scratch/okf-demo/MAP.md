# Map: Full working demo — LLM Wiki + OKF over pluggable local/xWiki storage

Labels: wayfinder:map
Status: ready-for-agent
Children: issues/01 … issues/10

## Destination

A working implementation per the ADRs — Router REPL + background watcher (`main.py`), MCP server (`mcp_server.py`), three Operations (Ingest/Query/Lint) over sandboxed file primitives — where wiki storage is **pluggable**: local disk `WIKI_DIR`, or a **self-hosted xWiki reached via MCP** (agent acts as MCP client; MCP is mandatory — if no viable xWiki MCP server exists we write a thin one wrapping xWiki's REST API). Raw sources and the watcher stay local-disk on both backends. Done = a scripted demo walkthrough (ingest → query → lint on local, then the same on xWiki) plus a small automated smoke-test suite covering primitives, OKF writing, and backend switching.

## Notes

- **Execution is in scope for this map** — the user asked to "plan and implement"; task tickets carry the build, not just decisions.
- Specs live in-repo: `docs/concepts/okf_spec.md` (OKF v0.1), `docs/concepts/llm-wiki.md` (LLM Wiki pattern). Project vocabulary: `CONTEXT.md`. Existing decisions: `docs/adr/0001–0010`.
- New architecture-shaping decisions from tickets should be recorded as ADRs (use /domain-modeling).
- Skills to use per ticket type: /research, /grilling, /domain-modeling, /prototype, /tdd for the build tickets.
- Toolchain confirmed on this machine: Docker 29.1.4, uv 0.10.3, Python 3.13.
- Charting-session decisions (pre-ticket, from grilling): pluggable storage backend (not sync, not source-only); xWiki self-hosted as the remote target; MCP transport mandatory; wiki side only is pluggable; done = scripted demo + smoke tests.
- Do not assume unstated requirements — user wants to be asked (HITL tickets are genuinely HITL).

## Decisions so far

<!-- one line per closed ticket -->

- [Research: xWiki MCP server landscape](issues/01-xwiki-mcp-landscape.md) — no viable existing xWiki MCP server (official one has no page CRUD; community ones immature); we build a thin Python `mcp` wrapper over xWiki's REST API (page CRUD + Solr search, HTTP Basic auth, markdown via the CommonMark syntax extension).
- [Grilling: storage abstraction design](issues/02-storage-abstraction-design.md) — five primitives stay the uniform LLM tool surface; `WikiStore` interface behind them; xWiki store = MCP client to our auto-spawned stdio page-CRUD server; client-side regex grep; `WIKI_BACKEND=local|xwiki`; `XWIKI_SPACE` is the write sandbox. Recorded as ADR 0011.
- [Task: stand up a local xWiki instance](issues/03-xwiki-instance.md) — xWiki 18.5.0 running at `http://localhost:8080` (`docker/docker-compose.yml` + idempotent `docker/setup_xwiki.py`); superadmin/xwiki-demo; markdown/1.2 verified over REST; extensions must be installed via a Groovy setup page, not `/rest/jobs` (see ticket for the gotcha).
- [Task: build core agent (local backend)](issues/08-core-agent-build.md) — built TDD-first in `wikiagent/` package + thin `main.py`/`mcp_server.py` entries; 31 tests, mypy clean; virtual `wiki/`/`sources/` paths route the two trees; Router carries a fourth deterministic `file_answer` tool (ADR 0006). Live-LLM verification deferred to ticket 10 (needs 07's credentials).
- [Grilling: OKF-on-xWiki mapping](issues/06-okf-on-xwiki-mapping.md) — OKF bundle maps to xWiki as **verbatim markdown/1.2 pages**: directory path → nested spaces under `XWIKI_SPACE`, filename → terminal page; frontmatter/body/links stored in-band unchanged; `index.md`/`log.md` → plain `index`/`log` pages. Export = walk+dump → byte-identical, conformant by construction. Recorded as ADR 0012.
- [Grilling: remote review gate](issues/05-remote-review-gate.md) — remote writes are gated by **ingest approval (ADR 0006) + xWiki's native page history** (diff/rollback); no preview/staging layer. Amends ADR 0004 to local-only. Recorded as ADR 0013.
- [Task: build xWiki backend (MCP client)](issues/09-xwiki-backend-build.md) — thin agent-agnostic xWiki MCP server (`wikiagent/xwiki_mcp_server.py`, FastMCP/stdio, 4 page tools over REST) + `XWikiStore` MCP client (`store.py`) auto-spawning it via a persistent stdio session on a worker-thread event loop (`xwiki_client.py`). `WIKI_BACKEND=xwiki` + `XWIKI_*` config; `list_pages` uses the wiki-wide `/pages?space=` endpoint (per-space `/spaces` misses WebHome-less nested spaces — the gotcha). 44 tests incl. a live round-trip verified against real xWiki; mypy clean.

## Not yet specified

- Lint semantics on the remote backend — what "orphan page" / "missing cross-reference" means over xWiki links; sharpens after the OKF-on-xWiki mapping is decided.
- Demo walkthrough details: exact beats, sample source files, what's shown live vs pre-baked — sharpens after the demo content domain is chosen.
- Query's HTML answer rendering details (template, browser-open mechanism) — minor; resolves inside the core-skeleton build ticket.
- Which new ADRs to write for pluggable storage and remote review-gate — falls out of the design tickets.

## Out of scope

- Slack integration & cloud hosting — [ADR 0009](../../docs/adr/0009-slack-out-of-scope.md).
- Obsidian integration — [ADR 0010](../../docs/adr/0010-no-obsidian-integration.md).
- Agent-driven git operations — [ADR 0004](../../docs/adr/0004-git-stays-manual.md).
- Confluence Cloud as the remote backend — considered during charting, user chose xWiki (offline, self-hosted).
- Two-way local↔remote sync — rejected during charting in favor of a pluggable backend (one storage world per session).
- Remote raw sources — sources and the watcher stay local on both backends (charting decision).
