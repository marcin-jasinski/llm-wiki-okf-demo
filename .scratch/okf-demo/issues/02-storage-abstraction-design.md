# Grilling: storage abstraction design

Labels: wayfinder:grilling
Status: ready-for-human
Blocked-by: 01-xwiki-mcp-landscape
Map: ../MAP.md

## Question

What interface do the three Operations see over pluggable storage? Do the five file primitives (`read_file`, `write_file`, `list_dir`, `grep`, `fetch_url`) stay the tool surface with a remote implementation behind them, or does the backend interface differ (e.g. `grep` becomes xWiki search; `fetch_url` stays backend-independent)? How is the backend selected (`.env` `STORAGE_BACKEND=local|xwiki`?) and is it fixed per session? How does the write sandbox rule ("writes only inside WIKI_DIR") translate to xWiki (writes only inside one space?)? Outcome: a decided interface + config story, recorded as an ADR.
