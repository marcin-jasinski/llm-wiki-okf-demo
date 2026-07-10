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
