# Agent is a tool-calling loop, not a scripted pipeline

The LLM decides which files to read/write via function calling against a small toolset, rather than our code hard-coding the ingest/query/lint steps and only calling the LLM for content generation. This matches what "AI agent" means for this demo — watching the LLM decide what to read and write is the point of the talk — and mirrors the LLM Wiki pattern's own premise of a general agent operating over a schema doc, not a fixed pipeline.

**Trade-off accepted**: tool-calling loops are less predictable than scripted flows, especially with weaker local models via LM Studio. Mitigated by controlling the demo's source documents and picking a capable local model.
