# Demo walkthrough — ingest → query → lint, on local disk then xWiki

This is the scripted showcase: the same agent maintaining the same OKF wiki,
first on local-disk storage, then on a self-hosted xWiki — with only a one-line
`.env` change between them (ADR 0011). The knowledge domain is a fictional SaaS
company, **Meridian**, whose engineering docs live in `demo/sources/`.

The five raw sources interlock on purpose so every Operation has something to
show:

- **Checkout depends synchronously on Billing** and fails closed, so a Billing
  outage stops all orders — that's the Query beat.
- **The Ledger service is referenced by four docs but has no design doc of its
  own** (the postmortem even says "write one") — that's the Lint beat.

## Prerequisites

- `uv` (this repo's runner) and Python 3.13.
- An LLM backend with **function calling**:
  - **LM Studio** with a tool-capable model loaded (the run below used
    `qwen/qwen3.5-9b`), or
  - an **OpenRouter** API key + a tool-capable `MODEL_NAME`.
- For the xWiki half: Docker, and the demo xWiki stood up once (see below).

## Setup

Copy `.env.example` to `.env` and fill it in. For the local backend:

```
WIKI_DIR=<repo>/demo/wiki
RAW_SOURCES_DIR=<repo>/demo/sources
WIKI_BACKEND=local

LLM_BACKEND=lmstudio
MODEL_NAME=<openrouter-model-id>          # used when LLM_BACKEND=openrouter
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen/qwen3.5-9b            # used when LLM_BACKEND=lmstudio
```

> `WIKI_DIR` and `RAW_SOURCES_DIR` must not overlap — point `WIKI_DIR` at
> `demo/wiki` (a sibling of `demo/sources`), never at `demo` itself, or the
> wiki store would treat the raw sources as concept pages. `demo/wiki/` is
> gitignored — it is regenerated live by this walkthrough.

## Part 1 — local backend

Start the single entry point (background watcher + Router REPL, ADR 0008):

```
uv run main.py
```

You'll see a banner like `wiki: local, llm: lmstudio/qwen/qwen3.5-9b`.

### Ingest

Two ways to ingest — both hit the same Ingest Operation:

- **Drop a file** into `demo/sources/` and the background watcher picks it up
  automatically, or
- **Ask the Router** in the REPL:

```
> ingest sources/billing-service-design.md
```

Ingest each of the five sources (order doesn't matter):

```
sources/billing-service-design.md
sources/checkout-service-design.md
sources/checkout-outage-runbook.md
sources/oncall-policy.md
sources/incident-2026-04-postmortem.md
```

**Expected:** each ingest reads the source, reads `wiki/index.md` and related
pages, then writes typed OKF concept pages, a source-summary page, and updates
`wiki/index.md` + `wiki/log.md`. After all five, `demo/wiki/` holds a
cross-linked bundle — services, a runbook, an on-call policy, and an incident,
each with YAML frontmatter (`type:`), plus `index.md`, `log.md`, and per-source
summaries. Exact page paths vary by model run; the tree from a real
`qwen/qwen3.5-9b` run:

```
index.md
log.md
services/billing.md
services/checkout.md
dependencies/ledger-service.md   # created as a dependency page though it has no source doc
dependencies/payrail.md
runbooks/checkout-outage-runbook.md
oncall-policy.md
incidents/postmortem-2026-04-12.md
sources/…                        # one summary per ingested source
```

### Query

```
> what's the blast radius if the billing service goes down?
```

Query is read-only; it reads `index.md`, greps for the relevant terms, reads
the pages it finds, and answers — then opens the answer as a styled HTML page
in your browser.

**Expected:** an answer synthesized across several pages — Billing charges
customers and issues invoices; Checkout calls it synchronously and **fails
closed**, so no new orders can be placed storefront-wide; Payments on-call is
paged (Sev1 if orders are fully stopped) — citing the billing, checkout, and
on-call pages as bundle-relative links.

A real `qwen/qwen3.5-9b` answer (abridged):

> **Direct impact — complete stop to order placement.** Checkout has a hard
> runtime dependency on Billing, calling `POST /charges` synchronously on the
> critical path. Because Checkout **fails closed** — releasing inventory and
> returning errors without creating an order — all new orders across the
> storefront halt. Shoppers can still browse and build carts, but checkout
> fails at payment.
> **Severity — Sev1**, because new orders are fully stopped; Billing's charge
> success rate falling below 95% also trips Sev1 alerts.
> **Response.** Storefront on-call escalates to **Payments on-call**; the
> checkout-outage runbook says check Billing health first, then PayRail, then
> Ledger.
>
> — citing `services/checkout.md`, `services/billing.md`,
> `runbooks/checkout-outage-runbook.md`.

### Lint

```
> lint the wiki
```

**Expected:** Self-Healing Lint (ADR 0007) fixes *structural* issues only —
adds any page missing from `index.md`, links orphan pages, and adds
cross-reference links for concepts mentioned but not linked (the **Ledger
service**, referenced across billing, the runbook, and the postmortem, is the
planted case). It appends a lint entry to `log.md` and reports any
*content-level* issues (contradictions, staleness) it deliberately left alone.

**Model caveat — this is the beat that wants a capable model.** Lint first runs
a mechanical OKF conformance scan (deterministic, backend-agnostic), then hands
the *structural* fixes to the LLM. In a real run the wiki had a genuine gap —
`incidents/postmortem-2026-04-12.md` was created during ingest but never added
to `index.md`, so Lint should add that entry and link the page. But the two
models tested here don't reliably converge on the fix: `qwen/qwen3.5-9b`
explores every page and hits the iteration cap without writing, and
`xiaomi/mimo-v2.5` (OpenRouter) returned an empty report. This is ADR
[`0002`](docs/adr/0002-tool-calling-loop.md)'s accepted trade-off — weaker
models are less predictable inside a tool-calling loop. **Ingest and Query are
robust on the local model; Lint's self-healing writes benefit from a frontier
model.** Point `LLM_BACKEND`/`MODEL_NAME` at one for this beat.

To see the self-heal concretely with a capable model, plant an obvious defect
first — delete one page's line from `index.md` — then run lint and watch it
restore the entry and append a `log.md` lint record.

### File an answer (optional)

Query never writes. To keep an answer as a page, ask explicitly (ADR 0006):

```
> file that answer under wiki/answers/billing-blast-radius.md
```

The Router files the previous answer verbatim, wrapped as a `Query Answer`
concept page.

## Part 2 — same demo on xWiki

Stand up the demo xWiki once (idempotent):

```
cd docker && docker compose up -d
uv run docker/setup_xwiki.py          # enables superadmin + markdown/1.2
```

Then flip **one section** of `.env` — the storage backend — and set the xWiki
target space (the write sandbox, ADR 0012):

```
WIKI_BACKEND=xwiki
XWIKI_BASE_URL=http://localhost:8080
XWIKI_USER=superadmin
XWIKI_PASSWORD=xwiki-demo
XWIKI_SPACE=WikiDemo
```

Nothing else changes — the raw sources, the Operations, and the prompts are all
identical. Run `uv run main.py` again (banner now reads `wiki: xwiki`) and
repeat the **same** ingest → query → lint beats.

**What's different under the hood** (invisible to the LLM): the five file
primitives now route through the xWiki Wiki Store, which drives our thin xWiki
MCP server (auto-spawned over stdio) to create pages in the `WikiDemo` space as
verbatim `markdown/1.2` documents. `demo/sources/tables/orders.md`-style paths
become nested xWiki pages; frontmatter and cross-links are stored in-band, so
exporting the space reproduces a conformant OKF bundle byte-for-byte (ADR 0012).

**Review gate:** there's no `git diff` on xWiki. Writes are gated by the same
ingest approval (ADR 0006) and audited/rolled back via xWiki's native page
**History** tab (ADR 0013). Open `http://localhost:8080` and browse the
`WikiDemo` space to see the pages and their revision history.

## Verifying conformance

At any point, a mechanical OKF conformance scan over the wiki should pass:

```
uv run python -c "from wikiagent.okf import check_bundle; \
print(check_bundle('demo/wiki') or 'CONFORMANT')"
```

(The xWiki backend is verified the same way via an export; the store's
`walk()` + `read()` reproduce the bundle.)

## Notes for presenting

- The local model (`qwen/qwen3.5-9b`) is capable but slower and less
  deterministic than a frontier model over OpenRouter — flip `LLM_BACKEND`
  and `MODEL_NAME` for a snappier "same agent, different brain" beat (ADR 0003).
- Page paths, titles, and prose vary run to run; the *structure* (typed
  frontmatter, index/log, cross-links, conformance) is what's stable.
