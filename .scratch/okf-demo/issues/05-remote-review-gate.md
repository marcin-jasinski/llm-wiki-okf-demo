# Grilling: human review gate for remote writes

Labels: wayfinder:grilling
Status: closed (2026-07-11)
Blocked-by: 01-xwiki-mcp-landscape
Map: ../MAP.md

## Question

ADR 0004's review story ("after any write, review `git diff` and commit by hand") has no analog when the wiki lives in xWiki. What is the human-review gate for remote writes — rely on xWiki's native page history/diff, a dry-run/preview mode before writes land, or accept direct writes for the demo? Outcome: a decision recorded as an ADR (possibly amending 0004's scope to local-only).
