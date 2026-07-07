# Self-healing Lint is limited to structural fixes

Lint writes fixes directly (orphan pages, missing cross-references, unlinked mentioned concepts) rather than only reporting them, but it does not attempt content-level judgment calls — resolving contradictions between pages, or marking claims as stale — automatically, even though the LLM Wiki spec lists both under the same "Lint" operation.

Structural fixes are low-risk and mechanically verifiable; auto-rewriting content because the LLM judged something "wrong" or "stale" is a much bigger, less reversible claim to make unsupervised. The line is drawn at mechanical vs. judgment-based fixes.
