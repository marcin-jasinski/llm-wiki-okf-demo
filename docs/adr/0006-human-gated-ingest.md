# Filing a Query answer into the wiki is always human-triggered, never LLM-decided

`query_wiki` is read-only (no `write_file` tool available during a query); the answer is rendered to HTML and opened in the browser. The write to the wiki only happens when the human explicitly says so (e.g. types "ingest it" to the Router), at which point the write is a deterministic wrap-with-frontmatter-and-save — not a second LLM judgment call, so the stored page is guaranteed identical to what was shown and approved.

Rejected letting the LLM decide autonomously to file good answers back into the wiki (an option the LLM Wiki spec's own "Query" section suggests) because unsupervised persistence decisions are exactly the kind of consequential action that should stay under human control, especially live on stage.
