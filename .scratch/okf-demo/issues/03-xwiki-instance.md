# Task: stand up a local xWiki instance

Labels: wayfinder:task
Status: closed (2026-07-10)
Assignee: agent (claimed 2026-07-10)
Blocked-by: —
Map: ../MAP.md

## Question

Get a self-hosted xWiki running locally via Docker (Docker 29 confirmed available): compose file checked into the repo (`docker/` or similar), verify the REST API answers (create/read a test page), record base URL, admin credentials location, and xWiki version. Per the [MCP landscape research](../assets/01-xwiki-mcp-landscape.md): also install the CommonMark Markdown Syntax 1.2 extension (`syntax-markdown-commonmark12`) and verify `markdown/1.2` appears in `/rest/syntaxes`. Resolution records these facts for later tickets.

## Comments

**Resolution (2026-07-10):** Running and verified. `docker/docker-compose.yml` (xwiki:stable-postgres-tomcat + postgres:16, named volumes) plus an idempotent `docker/setup_xwiki.py` (`uv run docker/setup_xwiki.py`) that does everything first-run: enables superadmin, installs the CommonMark Markdown Syntax 1.2 extension **and** the standard main-wiki flavor, disables the Distribution Wizard, and verifies. Facts for later tickets:

- **xWiki version**: 18.5.0 (image `xwiki:stable-postgres-tomcat`). Base URL: `http://localhost:8080`, REST at `/rest`.
- **Credentials**: `superadmin` / `xwiki-demo`, set via `xwiki.superadminpassword` in `xwiki.cfg` (config persisted to the permanent-directory volume; local demo only). HTTP Basic works on both `/rest` and `/bin`.
- **Markdown**: `syntax-markdown-commonmark12` 8.9 installed; `markdown/1.2` listed in `/rest/syntaxes` (requires `xwiki.rendering.syntaxes=xwiki/2.1,markdown/1.2` in `xwiki.cfg` — the REST endpoint reflects that config key, not what's installed). Verified create → read → delete of a `markdown/1.2` page over REST; content round-trips verbatim.
- **Gotcha for ticket 09**: the generic `PUT /rest/jobs?jobType=install` endpoint can't install extensions — its XStream payload can't populate `ExtensionId`'s final `version` field (NPE). The working automation is a superadmin-only Groovy page calling `services.extension.install(...)`, executed via one authenticated `GET /bin/get/...` (what `setup_xwiki.py` does), then deleted.
- UI verified: `/bin/view/Main/` renders (HTTP 200, no wizard redirect).
