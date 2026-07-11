# Remote writes are gated by ingest approval + xWiki's native history

ADR 0004's review story — "after any write the presenter reviews `git diff` and commits by hand" — is local-only; there is no git when the wiki lives in xWiki. For the xWiki backend the human-review gate is **the ingest approval that already happens (ADR 0006) plus xWiki's built-in page history for post-hoc audit and rollback**. No preview/staging layer is added.

The content of a filed page is already human-approved before any write: ADR 0006 keeps Ingest human-gated, so a person signs off on the concept document before `put_page` ever runs. What git gave on top of that was an *after-the-fact* record and an easy revert — and xWiki provides both natively: every page edit is a numbered revision with a diff view and one-click rollback in the page History tab. So the remote gate loses nothing the local one had.

This amends ADR 0004's scope to **local-disk backend only**; its reasoning (never expose git tools to the LLM; keep consequential, hard-to-reverse actions out of the loop) is unchanged for the local backend.

Rejected a dry-run/preview mode that stages page writes for confirmation before they land: it re-implements, in application code and only for the remote backend, a review step ADR 0006 already performs at ingest time and that xWiki's versioning already backstops — pure duplication. Rejected accepting ungated direct writes with no audit story: it would drop the human-in-the-loop principle ADR 0004/0006 established, and xWiki history makes the audited path free anyway.
