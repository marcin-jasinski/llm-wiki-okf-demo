# Self-healing Lint is limited to structural fixes

Lint writes fixes directly (orphan pages, missing cross-references, unlinked mentioned concepts) rather than only reporting them, but it does not attempt content-level judgment calls — resolving contradictions between pages, or marking claims as stale — automatically, even though the LLM Wiki spec lists both under the same "Lint" operation.

Structural fixes are low-risk and mechanically verifiable; auto-rewriting content because the LLM judged something "wrong" or "stale" is a much bigger, less reversible claim to make unsupervised. The line is drawn at mechanical vs. judgment-based fixes.

Two refinements after the LLM proved too radical in practice — it would strip relevant prose while "fixing" structure, and its index updates were unreliable:

- **Index membership is deterministic, not LLM-driven.** `ensure_index_entries` mechanically appends an `index.md` catalog line for every page not already linked (never removing or reordering). It runs after Ingest and Lint, and after a Query answer is filed, so the catalog is always complete regardless of what the LLM did. Lint no longer touches the catalog at all.
- **Lint's page writes are content-additive only.** A `write_file` during Lint that makes a page meaningfully shorter is rejected — legitimate lint edits (inserting a cross-link, adding a `type:` field) only ever grow a page. This is the mechanical guard that stops the "removed too much" failure without trusting the prompt alone.
